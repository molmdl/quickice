# Phase 42: Mixed Cage Occupancy - Research

**Researched:** 2026-07-05
**Domain:** GenIce2 multi-guest hydrate generation, per-cage-type guest assignment, multi-guest GROMACS export, per-type VTK rendering
**Confidence:** HIGH (all core feasibility claims verified by running code against the live `quickice` conda env; every `file:line` citation read directly)

## Summary

Phase 42 extends hydrate generation so users can assign **different guest types to different cage types** with **independent occupancy percentages** (e.g. 60% CH₄ in small cages + 100% custom ethanol in large cages). The core finding is **highly encouraging**: GenIce2 **already natively supports mixed occupancy** — its `guests` dict (`genice2.valueparser.parse_guest`) can hold multiple cage types each mapping to a different molecule, and `generate_ice()` places them all in one pass. I verified this end-to-end by generating an sI 2×2×2 hydrate with CH₄ in all small cages + a custom ethanol (synthetic `sys.modules` plugin) in all large cages: **16 CH₄ + 48 MOL** molecules placed correctly (verified by residue-name counting). **No GenIce2 changes are required** — the entire phase is QuickIce-side wiring.

The work breaks down along the existing data-flow: (1) `HydrateConfig` gains a `cage_guest_assignments: dict[cage_key, CageGuestAssignment]` field (cage_key ∈ "small"/"medium"/"large"/"guest"; each entry = `{guest_type, occupancy, guest_residue_name?, guest_gro_path?, guest_itp_path?, guest_atom_labels?, guest_atom_count?}`); (2) `hydrate_generator._run_via_api` iterates the assignments and builds one `parse_guest` call per cage type with the per-cage guest name (and registers multiple custom-guest `sys.modules` entries via nested `custom_guest_module` context managers); (3) `_build_molecule_index` groups by residue name into per-guest-type `mol_type` (it already does this for one custom guest — extend to a set); (4) `HydrateStructure` carries a list of guest descriptors instead of a single one; (5) the GROMACS writers (`write_multi_molecule_*`, `write_interface_*`) accept a **list** of `custom_guest_info` dicts instead of one, and the existing per-`unique_type` `[ molecules ]` / `#include` / atomtypes-merge loops handle multiple guests with minimal change; (6) `hydrate_renderer.create_guest_actor` builds **one vtkMolecule per `mol_type`** so each guest type gets its own actor/color; (7) the GUI `HydratePanel` replaces the single guest combo + two occupancy spinboxes with a **per-cage-type row** (guest combo + occupancy spinbox), driven by the selected lattice's `cage_type_map` keys.

**Critical prerequisite discovery (HIGH confidence, verified by running code):** `HYDRATE_LATTICES["sH"]["cage_type_map"]` is **wrong** — it is `{"small": "12", "large": "16"}` but GenIce2's sH lattice has cage types `12` (small 5¹²), `12_1` (medium 4³5⁶6³), and `20` (large 5¹²6⁸). I proved `parse_guest(guests, "16=ch4*1.0")` on an sH lattice places **ZERO** large-cage guests (silent bug — no error, just empty large cages), while `parse_guest(guests, "20=ch4*1.0")` places 10. The `medium` key is **missing entirely**, so sH medium cages are unreachable. **MIXED-01 requires sH small/medium/large**, so this MUST be fixed before/at the start of Phase 42. Recommendation: **fix it as the first task of Phase 42** (2-line `types.py` edit + 1-line test update), not as a separate Phase 39 follow-up — it's tiny, Phase 42 cannot succeed without it, and Phase 39 is already closed (has VERIFICATION.md). The Phase 39 research *flagged* the `12_1`/`20` identifiers (39-RESEARCH.md line 359) but the shipped plan/impl used `16` anyway, so this is a latent bug, not a new discovery.

**Primary recommendation:** Add a `cage_guest_assignments` dict to `HydrateConfig` (backward-compatible with the existing single-guest fields via a `_legacy_to_assignments()` shim in `__post_init__`); make `_run_via_api` iterate it; thread a **list** of `custom_guest_info` dicts through the four GROMACS writers; make `create_guest_actor` return one actor per `mol_type`; and replace the GUI's single guest+occupancy row with a per-cage-type row built from `HYDRATE_LATTICES[lat]["cage_type_map"]`. Fix the sH `cage_type_map` (`large`→`"20"`, add `"medium"`→`"12_1"`) and the `test_hydrate_lattice_types.py` `valid_keys` set (add `"medium"`) as the very first task.

## Standard Stack

### Core (existing — REUSE, do not reinvent)

| Library / Module | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `genice2.valueparser.parse_guest` | 2.2.13.1 | Builds `guests` dict from `"cage=mol*frac"` spec; **already supports multi-guest** (different cage types → different molecules) | THE dict-builder; no GenIce2 change needed |
| `genice2.genice.GenIce.generate_ice` | 2.2.13.1 | Places all guests in one pass from the `guests` dict | Verified: CH₄+custom in one sI generation |
| `quickice.structure_generation.custom_guest_bridge` | existing | `build_custom_guest_module` + `custom_guest_module` context manager (sys.modules injection) | Phase 40; **nest two context managers for two custom guests** |
| `quickice.structure_generation.moleculetype_registry` | existing | `register_hydrate_guest` → `{name}_H`; `RESERVED_NAMES` | Reuse; **register each built-in guest** (ch4→CH4_H, thf→THF_H) |
| `quickice.output.gromacs_writer.transform_guest_itp` | existing | Step1 comment atomtypes, Step2 rename moleculetype `{name}_H`, Step3 rewrite `[atoms]` resname | Call once per custom guest ITP |
| `quickice.output.gromacs_writer._merge_custom_atomtypes` | existing | Parse ITP `[atomtypes]` → conflict-check → write-if-new → dedup | **Call once per custom guest** (the dedup dict accumulates across guests) |
| `quickice.structure_generation.gro_parser.parse_gro_file` | existing | Parse GRO, validate >50nm | Reuse per custom guest |
| `quickice.structure_generation.itp_parser.parse_itp_file` | existing | Parse ITP | Reuse per custom guest |
| `quickice.gui.hydrate_renderer.create_guest_actor` | existing | Builds ONE vtkMolecule from ALL non-water mols | **Extend: one vtkMolecule per `mol_type`** |

### Supporting (existing — EXTEND, not reinvent)

| File:Function | Line | Current (single-guest) | Phase 42 target (multi-guest) |
|---------------|------|------------------------|-------------------------------|
| `types.py::HydrateConfig` | 430 | `guest_type`, `cage_occupancy_small/large`, single `guest_*` metadata | Add `cage_guest_assignments: dict[str, CageGuestAssignment]`; keep legacy fields for backward compat |
| `hydrate_generator.py::_run_via_api` | 200-293 | Builds ONE `guest_name`, calls `parse_guest` for small+large with SAME guest | Iterate `cage_guest_assignments`: one `parse_guest` per cage_key with its own guest_name |
| `hydrate_generator.py::generate` | 102-198 | Builds+registers ONE custom module via `custom_guest_module` context manager | Nest one context manager per custom guest (or refactor to a multi-registration helper) |
| `hydrate_generator.py::_build_molecule_index` | 556-676 | Groups by ONE `guest_res_name`/`guest_type` | Group by a **set** of `(residue_name → mol_type)` mappings; emit per-guest-type `MoleculeIndex.mol_type` |
| `types.py::HydrateStructure` | 914-947 | Single `guest_name`, `guest_atom_labels`, `guest_atom_count`, `guest_itp_path` | Carry a **list** of guest descriptors (or derive from `molecule_index` + `config.cage_guest_assignments`) |
| `gromacs_writer.py::write_multi_molecule_gro_file` | 1596 | `custom_guest_info: dict \| None` (single) | `custom_guest_info: list[dict] \| None` (list); match `mol.mol_type` against any entry |
| `gromacs_writer.py::write_multi_molecule_top_file` | 1727 | single `custom_guest_info`; one atomtypes merge; `[molecules]` already iterates `unique_types` | `custom_guest_info: list[dict]`; **loop** the atomtypes merge over each custom ITP; `[molecules]`/`#include` loops already multi-guest (just need `itp_files` keyed by each mol_type) |
| `gromacs_writer.py::write_interface_gro_file` | 1043 | single `custom_guest_info` | `custom_guest_info: list[dict]` (CLI path) |
| `gromacs_writer.py::write_interface_top_file` | 1442 | single `custom_guest_info` | `custom_guest_info: list[dict]` (CLI path) |
| `cli/pipeline.py::_build_custom_guest_info` | 32 | Returns single dict or None | Return **list** of dicts (one per custom guest in the assignment) |
| `gui/hydrate_export.py::export_hydrate` | 90 | Single `custom_guest_info` + single `itp_files` + single `transform_guest_itp` | Build per-guest entries; loop `transform_guest_itp` per custom ITP; pass list to writers |
| `gui/hydrate_panel.py::HydratePanel` | 26-448 | Single `guest_combo` + `occupancy_small`/`occupancy_large` spinboxes | **Per-cage-type row**: for each key in `HYDRATE_LATTICES[lat]["cage_type_map"]`, a guest combo + occupancy spinbox |
| `gui/hydrate_renderer.py::create_guest_actor` | 391-484 | ONE vtkMolecule from ALL non-water mols; ONE actor | **One vtkMolecule per `mol_type`**; return `[actor_per_type...]`; color/style per type |
| `cli/parser.py` hydrate_group | 194-255 | `--guest` (CH4/THF), `--cage-occupancy-small/large` | Add `--cage-guest` repeatable: `--cage-guest small=CH4:60 --cage-guest large=custom:100` (or similar); keep legacy flags for backward compat |

### NEW (genuinely new code)

| Component | Purpose |
|-----------|---------|
| `CageGuestAssignment` dataclass (in `types.py`) | `{guest_type, occupancy, guest_residue_name="", guest_gro_path="", guest_itp_path="", guest_atom_labels=[], guest_atom_count=0}` — one entry per cage type |
| `HydrateConfig._legacy_to_assignments()` shim | When `cage_guest_assignments` is empty but `guest_type` is set, synthesize `{"small": CageGuestAssignment(guest_type, cage_occupancy_small), "large": CageGuestAssignment(guest_type, cage_occupancy_large)}` — backward compat |
| Multi-registration helper in `hydrate_generator.generate` | Nest `custom_guest_module` context managers for each custom guest in the assignment (or build a `multi_custom_guest_modules` context manager) |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `cage_guest_assignments: dict[str, CageGuestAssignment]` | Keep single `guest_type` + add `guest_type_large`, `guest_type_medium`... | Explodes field count; doesn't scale to filled ices ("guest" key); dict is the natural shape matching `cage_type_map`. **Use the dict.** |
| Nested `custom_guest_module` context managers | A new `multi_custom_guest_modules(assignments)` context manager | Nesting 2-3 managers is fine (Python supports it cleanly); a multi-helper is cleaner if ≥3 guests. **Recommend the helper** for readability. |
| New `--cage-guest` repeatable CLI flag | Per-cage-type fixed flags (`--guest-small`, `--guest-large`, `--guest-medium`) | Repeatable flag is more flexible and matches filled-ices ("guest" key); fixed flags are simpler to parse. **Recommend repeatable `--cage-guest key=value`** but keep `--guest`/`--cage-occupancy-*` as deprecated aliases. |
| Per-type actors in `create_guest_actor` | Per-atom scalar coloring via `vtkArray` in one actor | vtkMoleculeMapper doesn't expose easy per-atom color overrides; separate actors are the existing pattern (water vs guest already separate). **Use per-type actors.** |

**Installation:**
```bash
# No new dependencies. Uses only stdlib + existing quickice modules + genice2 (already installed).
# Do NOT add anything to environment.yml for this phase.
```

## Architecture Patterns

### Recommended Project Structure (files touched)
```
quickice/
├── structure_generation/
│   ├── types.py                   # MODIFY: add CageGuestAssignment dataclass; HydrateConfig.cage_guest_assignments; HydrateStructure multi-guest; FIX sH cage_type_map
│   ├── hydrate_generator.py       # MODIFY: _run_via_api iterate assignments; generate() multi-register custom modules; _build_molecule_index multi-guest grouping
│   └── custom_guest_bridge.py     # REUSE as-is (call build_custom_guest_module per custom guest)
├── output/
│   └── gromacs_writer.py          # MODIFY: write_multi_molecule_{gro,top}_file + write_interface_{gro,top}_file accept list[dict] custom_guest_info; loop atomtypes merge
├── gui/
│   ├── hydrate_panel.py           # MODIFY: per-cage-type guest+occupancy rows driven by cage_type_map
│   ├── hydrate_export.py          # MODIFY: build per-guest custom_guest_info list + itp_files dict; loop transform_guest_itp
│   ├── hydrate_renderer.py        # MODIFY: create_guest_actor returns one actor per mol_type; render_hydrate_structure returns [water, guest1, guest2, ...]
│   └── hydrate_viewer.py          # MODIFY: handle variable-length actor list; per-type visibility toggles
├── cli/
│   ├── parser.py                  # MODIFY: add --cage-guest repeatable; keep --guest/--cage-occupancy-* as deprecated aliases
│   └── pipeline.py                # MODIFY: _build_custom_guest_info returns list; HydrateConfig build from --cage-guest
└── data/custom/                   # EXISTING etoh.gro/etoh.itp fixtures (reuse for multi-guest tests)
tests/
├── test_hydrate_lattice_types.py  # MODIFY: valid_keys add "medium"; add sH large=="20", medium=="12_1" assertions
├── test_e2e_mixed_cage_occupancy.py  # NEW: multi-guest generation + export + grompp + rendering
└── test_hydrate_config_custom.py   # EXTEND: cage_guest_assignments validation tests
```

### Pattern 1: `cage_guest_assignments` data model (THE central change)
**What:** `HydrateConfig` carries a dict mapping each cage key to a `CageGuestAssignment`. The keys come from `HYDRATE_LATTICES[lattice_type]["cage_type_map"]` (e.g. sI → {"small","large"}; sH → {"small","medium","large"}; filled ices → {"small"} (which maps to "Ne1" — single cage); water-only → {}).
**When to use:** Always for Phase 42. Backward-compatible via `_legacy_to_assignments()`.
**Why:** Matches GenIce2's `guests` dict shape (`{cagetype: {molec: frac}}`) and the `cage_type_map` shape. One assignment per cage type → one `parse_guest` call per cage type → independent guest_name + occupancy per cage.

```python
# Source: new in types.py (Phase 42)
@dataclass
class CageGuestAssignment:
    """One guest assignment for one cage type."""
    guest_type: str                          # "ch4", "thf", or a custom slug
    occupancy: float = 100.0                 # 0-100 percent
    # Custom-guest metadata (empty for built-ins; required when guest_type not in GUEST_MOLECULES)
    guest_residue_name: str = ""
    guest_gro_path: str = ""
    guest_itp_path: str = ""
    guest_atom_labels: list[str] = field(default_factory=list)
    guest_atom_count: int = 0

    @property
    def is_custom_guest(self) -> bool:
        return self.guest_type not in GUEST_MOLECULES

# HydrateConfig gains:
@dataclass
class HydrateConfig:
    # ... existing fields kept for backward compat ...
    cage_guest_assignments: dict[str, CageGuestAssignment] = field(default_factory=dict)

    def __post_init__(self):
        # ... existing validation ...
        # Backward-compat shim: if cage_guest_assignments is empty but guest_type is set,
        # synthesize from the legacy single-guest fields.
        if not self.cage_guest_assignments and self.guest_type:
            lattice_entry = HYDRATE_LATTICES[self.lattice_type]
            cmap = lattice_entry.get("cage_type_map", {})
            self.cage_guest_assignments = {}
            if "small" in cmap:
                self.cage_guest_assignments["small"] = CageGuestAssignment(
                    guest_type=self.guest_type, occupancy=self.cage_occupancy_small,
                    guest_residue_name=self.guest_residue_name,
                    guest_gro_path=self.guest_gro_path,
                    guest_itp_path=self.guest_itp_path,
                    guest_atom_labels=list(self.guest_atom_labels),
                    guest_atom_count=self.guest_atom_count,
                )
            if "large" in cmap:
                self.cage_guest_assignments["large"] = CageGuestAssignment(
                    guest_type=self.guest_type, occupancy=self.cage_occupancy_large,
                    # ... same custom metadata ...
                )
            # medium / guest keys handled by iterating cage_type_map below
```

### Pattern 2: Multi-guest `_run_via_api` (the generator core)
**What:** Iterate `cage_guest_assignments`; for each `(cage_key, assignment)`, resolve the GenIce2 cage id from `cage_type_map[cage_key]` and call `parse_guest(guests, f"{cage_id}={guest_name}*{frac}")`.
**When to use:** Always (replaces the single-guest small/large branch at lines 262-277).
**Verified:** the `guests` dict accepts multiple cage types with different molecules (my POC: `{"12": {"ch4": 1.0}, "14": {"etoh_mix": 1.0}}` → 16 CH₄ + 48 MOL).

```python
# Source: hydrate_generator.py::_run_via_api (Phase 42 replacement of lines 238-277)
guests = defaultdict(dict)
lattice_entry = HYDRATE_LATTICES[config.lattice_type]
cage_type_map = lattice_entry.get("cage_type_map", {})
is_water_only = lattice_entry.get("is_water_only", False)

# Build a name lookup: guest_type -> GenIce2 plugin name (built-ins lowercased; custom = guest_type slug)
def _genice_name(guest_type: str) -> str:
    return guest_type if guest_type not in ("ch4", "thf") else guest_type

if not is_water_only:
    for cage_key, assignment in config.cage_guest_assignments.items():
        if cage_key not in cage_type_map:
            logger.warning("cage_key %r not in cage_type_map for %s; skipping",
                           cage_key, config.lattice_type)
            continue
        if assignment.occupancy <= 0:
            continue
        cage_id = cage_type_map[cage_key]
        guest_name = _genice_name(assignment.guest_type)
        frac = assignment.occupancy / 100.0
        guest_spec = f"{cage_id}={guest_name}" if frac >= 1.0 else f"{cage_id}={guest_name}*{frac}"
        parse_guest(guests, guest_spec)   # NOTE: parse_guest asserts cagetype not already in guests
                                          # — different cage_keys → different cage_ids → no collision
```

### Pattern 3: Multi-custom-guest `sys.modules` registration
**What:** For each custom guest in the assignment, `build_custom_guest_module` + nest a `custom_guest_module` context manager. All built on the **main thread** before `_run_via_api` runs; all cleaned up via `try/finally`.
**When to use:** When ≥1 assignment is a custom guest.
**Why:** `safe_import('molecule', guest_type)` is called per guest_type in Stage7; each distinct custom guest needs its own `sys.modules["genice2.molecules.<guest_type>"]` entry. The `custom_guest_module` context manager asserts key-absent on entry (line 346) and pops on exit — **nesting works** because each key is distinct.

```python
# Source: hydrate_generator.py::generate (Phase 42 extension of lines 136-165)
custom_assignments = {k: a for k, a in config.cage_guest_assignments.items()
                      if a.is_custom_guest}
if custom_assignments:
    from contextlib import ExitStack
    from quickice.structure_generation.custom_guest_bridge import (
        build_custom_guest_module, custom_guest_module,
    )
    # ExitStack lets us enter a VARIABLE number of context managers cleanly
    # (one per custom guest) and guarantees all are cleaned up on exit.
    with ExitStack() as stack:
        for cage_key, assignment in custom_assignments.items():
            module = build_custom_guest_module(
                assignment.guest_gro_path,
                assignment.guest_type,
                assignment.guest_residue_name,
            )
            stack.enter_context(custom_guest_module(assignment.guest_type, module))
        positions, cell, atom_names, residue_names, residue_seq_nums = (
            self._run_via_api(lattice_name, config)
        )
else:
    positions, cell, atom_names, residue_names, residue_seq_nums = (
        self._run_via_api(lattice_name, config)
    )
```
**Verified pattern:** `ExitStack` is stdlib (`contextlib`) and is the canonical way to manage N context managers. The Phase 40 POC used a single `with custom_guest_module(...)`; nesting 2-3 is equivalent.

### Pattern 4: Multi-guest `_build_molecule_index` (residue-name grouping)
**What:** Build a `{residue_name → mol_type}` lookup from ALL assignments (not just one `guest_res_name`), then group atoms by residue name → emit the per-guest-type `mol_type`.
**When to use:** When `config.cage_guest_assignments` has ≥1 entry.
**Why:** GenIce2 writes the residue name (`Molecule.name_`) per guest. For mixed ch4+custom, residues are "CH4" and "MOL". The current code (line 609, 617) checks `residue == guest_res_name` for ONE name; extend to a dict.

```python
# Source: hydrate_generator.py::_build_molecule_index (Phase 42 extension of lines 596-627)
# Build residue_name -> mol_type map from ALL assignments
resname_to_moltype: dict[str, str] = {}
atomlabel_to_meta: dict[str, tuple[list[str], int]] = {}  # mol_type -> (labels, count)
for cage_key, assignment in config.cage_guest_assignments.items():
    if assignment.guest_type in GUEST_MOLECULES:
        res_name = assignment.guest_type.upper()   # ch4 -> "CH4"
    else:
        res_name = assignment.guest_residue_name or assignment.guest_type.upper()
    resname_to_moltype[res_name] = assignment.guest_type
    atomlabel_to_meta[assignment.guest_type] = (assignment.guest_atom_labels,
                                                 assignment.guest_atom_count)

# In the grouping loop (replaces lines 617-627):
if residue in resname_to_moltype and residue_seq_nums is not None:
    mol_type = resname_to_moltype[residue]
    guest_seq = residue_seq_nums[i]
    guest_start = i
    j = i
    while j < len(residue_seq_nums) and residue_seq_nums[j] == guest_seq:
        guest_count += 1; j += 1
    molecule_index.append(MoleculeIndex(guest_start, guest_count, mol_type))
    i = j; continue
```

### Pattern 5: Multi-guest GROMACS export (`list[dict]` custom_guest_info)
**What:** The four writers accept `custom_guest_info: list[dict] | None` (was `dict | None`). The `[ molecules ]` and `#include` loops **already iterate `unique_types`** (verified: lines 1773-1807, 1810-1820) — so they handle multiple guest types with NO change to the loop structure. Only the `res_name` resolution (lines 1797-1804) and the atomtypes merge (lines 1883-1889) need to consult the **list**.
**When to use:** All four hydrate export writers.

```python
# Source: gromacs_writer.py::write_multi_molecule_top_file (Phase 42 — res_name resolution)
# custom_guest_info is now a list[dict] (or None)
custom_by_moltype = {ci["mol_type"]: ci for ci in (custom_guest_info or [])}

for mol_type in unique_types:
    res_name = None
    if registry:
        hydrate_key = f"hydrate_{mol_type.upper()}"
        if hydrate_key in reg._registered:
            res_name = reg.get_gromacs_name(hydrate_key)
    if res_name is None:
        if mol_type in custom_by_moltype:
            res_name = custom_by_moltype[mol_type]["residue_name"]
        elif mol_type in ["ch4", "thf", "co2", "h2"]:
            res_name = get_guest_residue_name(mol_type)
        else:
            res_name = MOLECULE_TO_GROMACS.get(mol_type, {"mol_name": "UNK"})["mol_name"]
    ...

# Atomtypes merge (Phase 42 — loop over each custom ITP):
for ci in (custom_guest_info or []):
    if ci.get("itp_path"):
        _merge_custom_atomtypes(
            f, Path(ci["itp_path"]), _written_atomtypes,
            f"custom guest {ci['mol_type']} atom types",
        )
# The _written_atomtypes dict accumulates across guests → dedup across all custom ITPs
```

### Pattern 6: Per-type VTK rendering (one actor per `mol_type`)
**What:** `create_guest_actor` groups `molecule_index` entries by `mol_type` (excluding water), builds a separate `vtkMolecule` per group, and returns one `vtkActor` per group. `render_hydrate_structure` returns `[water_actor, guest_actor_1, guest_actor_2, ...]`.
**When to use:** Always for Phase 42 (the current single-actor path still works for the 1-guest case by producing a 1-element list).

```python
# Source: hydrate_renderer.py::create_guest_actor (Phase 42 — replace lines 391-484)
def create_guest_actor(structure, mode="ball_and_stick",
                       per_type_colors: dict[str, tuple] | None = None) -> list[vtkActor]:
    """Return one actor per guest mol_type (empty list if no guests)."""
    # Group molecule_index by mol_type (excluding water)
    from collections import defaultdict
    by_type = defaultdict(list)
    for mol in structure.molecule_index:
        if mol.mol_type != "water":
            by_type[mol.mol_type].append(mol)
    if not by_type:
        return []  # or [empty hidden actor] for backward compat
    actors = []
    for mol_type, mols in by_type.items():
        molecule = vtkMolecule()
        for mol in mols:
            start, end = mol.start_idx, mol.start_idx + mol.count
            # ... append atoms + intra-molecule bonds (existing logic, lines 419-447) ...
        _set_molecule_lattice(molecule, structure.cell)
        mapper = vtkMoleculeMapper()
        mapper.SetInputData(molecule)
        # ... mode settings ...
        # Per-type color (default: cycle through a palette; caller can override)
        color = (per_type_colors or {}).get(mol_type, (180, 180, 180))
        mapper.SetBondColor(*color)
        actor = vtkActor(); actor.SetMapper(mapper)
        actors.append(actor)
    return actors
```
**Note:** `render_hydrate_structure` (line 487) returns `[water_actor, guest_actor]` (2-element); callers (`hydrate_viewer.py` line 246, `interface_viewer.py` line 225) index `[1]` for the guest. **This is a breaking change** — callers must handle a variable-length list. See Open Questions Q3.

### Anti-Patterns to Avoid
- **Calling `parse_guest` twice with the SAME cage id:** `parse_guest` asserts `cagetype not in guests` (valueparser.py:62) — crashes with "Cage type already specified." Each cage_key → distinct cage_id (small→12, large→14 for sI) so this is safe, but **never reuse a cage_id across assignments**.
- **Registering two custom guests under the SAME `guest_type`:** `custom_guest_module` asserts key-absent (line 346). Each custom guest MUST have a unique slug.
- **Leaking `sys.modules` entries on exception:** always use `try/finally` (the `ExitStack` pattern guarantees this).
- **Passing `config.guest_type.upper()` to `transform_guest_itp` for a custom guest:** produces >5-char names → `ValueError` (Phase 41 Pitfall 2). Use `guest_residue_name` per assignment.
- **Hardcoding `["ch4","thf","co2","h2"]` gates** in writers (lines 1663, 1680, 1800): exclude custom `mol_type`s. Use the `custom_by_moltype` lookup.
- **Forgetting the sH `cage_type_map` fix:** without it, sH large cages silently get ZERO guests and sH medium is unreachable (MIXED-01 fails). Fix FIRST.
- **Breaking `HydrateLatticeInfo.from_lattice_type`:** it iterates `lattice["cages"].items()` (line 896) which for sH already yields small/medium/large — so `cage_types`/`cage_counts` are correct; only `cage_type_map` was wrong. Don't "fix" the cages dict.
- **Bare `except Exception`** in `quickice/cli/pipeline.py` (AGENTS.md forbids it).
- **`git add .` / `git add -A`**: AGENTS.md mandates atomic commits.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Multi-guest `guests` dict construction | custom multi-cage dict builder | `parse_guest` per cage type (loop) | Already supports `{"12": {"ch4": 1.0}, "14": {"etoh": 1.0}}`; the `+` syntax even allows multiple guests IN one cage |
| Multi-custom-guest `sys.modules` registration | custom registration bookkeeping | `ExitStack` + `custom_guest_module` (nested) | stdlib `ExitStack` handles N context managers + guaranteed cleanup |
| Per-guest ITP transformation | new per-guest transform | `transform_guest_itp(content, guest_residue_name, "_H")` per custom ITP | Phase 40/41 already complete; just call once per custom guest |
| Multi-IPP atomtypes dedup | custom cross-IPP dedup | `_merge_custom_atomtypes` in a loop; `_written_atomtypes` accumulates | Already triplicated; dedup dict persists across calls |
| `_H` suffix naming for multiple guests | string concat per guest | `MoleculetypeRegistry.register_hydrate_guest` per built-in | Reserved-name collision checks; consistent `_H` convention |
| Per-mol_type grouping for rendering | custom atom-name heuristics | `molecule_index` `mol_type` field (set by `_build_molecule_index`) | Metadata-driven (Phase 38/40); already distinguishes guest types |
| Cage-key → GenIce2-cage-id resolution | hardcode per lattice | `HYDRATE_LATTICES[lat]["cage_type_map"][cage_key]` | Single source of truth; Phase 39 established it |

**Key insight:** Every primitive needed for Phase 42 already exists — `parse_guest` (multi-cage), `custom_guest_module` (nestable), `transform_guest_itp` (callable per ITP), `_merge_custom_atomtypes` (callable per ITP), `MoleculeIndex.mol_type` (per-type), `create_guest_actor` (groupable). The work is **wiring** (a dict on `HydrateConfig` + loops in the generator/writers/renderer) and **fixing the sH `cage_type_map` bug**, not building new mechanisms.

## Common Pitfalls

### Pitfall 1: The sH `cage_type_map` bug (SILENT — places ZERO large-cage guests)
**What goes wrong:** `HYDRATE_LATTICES["sH"]["cage_type_map"] = {"small": "12", "large": "16"}`. GenIce2's sH lattice has cage types `12`, `12_1`, `20` — NOT `16`. `parse_guest(guests, "16=ch4*1.0")` on sH places **ZERO** guests (verified: `CH4_guests=0`). No error is raised. The user sets 100% large-cage occupancy and gets an empty-large-cage sH hydrate with no indication anything is wrong.
**Why it happens:** Phase 39 research (39-RESEARCH.md line 359) documented that sH uses `12`/`12_1`/`20`, but the shipped plan (39-01-PLAN.md line 71) set `large="16"` anyway — likely a copy-paste from sII. The bug was never caught because no test exercises sH large-cage occupancy with a guest-count assertion.
**How to avoid:** Fix `HYDRATE_LATTICES["sH"]["cage_type_map"]` to `{"small": "12", "medium": "12_1", "large": "20"}`. Add a regression test: `gen = HydrateStructureGenerator(); s = gen.generate(HydrateConfig(lattice_type="sH", guest_type="ch4", cage_occupancy_large=100.0)); assert s.guest_count > 0` and specifically assert large-cage guests are placed (count > small-only count).
**Warning signs:** sH hydrate with `cage_occupancy_large>0` but `guest_count` equals the small-cage-only count (30 for 1×1×1).
**Recommendation:** Fix as Phase 42's **first task** (42-00 prerequisite), not a separate Phase 39 follow-up. See "sH medium cage gap recommendation" below.

### Pitfall 2: `parse_guest` asserts cage-id uniqueness
**What goes wrong:** `parse_guest(guests, "12=ch4*0.6")` then `parse_guest(guests, "12=etoh*0.4")` → `AssertionError: Cage type already specified.` (valueparser.py:62).
**Why:** The assert forbids re-specifying the same cage id.
**How to avoid:** Each `cage_key` in `cage_guest_assignments` maps to a DISTINCT `cage_id` via `cage_type_map` — so no collision. BUT if two assignments somehow map to the same cage_id (e.g. filled ice "small"→"Ne1" + a stray "large"→"Ne1"), it crashes. **Validate** that all `cage_id`s resolved from `cage_guest_assignments` are unique before calling `parse_guest`. Note: GenIce2 DOES support multiple guests in ONE cage via the `+` syntax (`"12=ch4*0.6+etoh*0.4"`), but that's "mixed within a cage" — different from MIXED-01's "different guests in different cages". Don't conflate them.
**Warning signs:** `AssertionError: Cage type already specified.` during generation.

### Pitfall 3: `test_hydrate_lattice_types.py` FORBIDS "medium" key
**What goes wrong:** `test_cage_type_map_keys_are_small_or_large` (line 77-81) asserts `key in {"small", "large"}`. Adding `"medium"` to sH's `cage_type_map` makes this test FAIL.
**Why:** The test was written before sH medium was supported (Phase 39 shipped `{"small","large"}` only).
**How to avoid:** Update `valid_keys = {"small", "large", "medium", "guest"}` (add "guest" too, for completeness/future-proofing, though filled ices currently use "small"). Add a specific sH test: `assert HYDRATE_LATTICES["sH"]["cage_type_map"] == {"small": "12", "medium": "12_1", "large": "20"}`.
**Warning signs:** Test failure after the types.py fix.

### Pitfall 4: Backward-compat with single-guest `HydrateConfig` construction
**What goes wrong:** Existing callers (GUI `hydrate_panel.get_configuration()` line 440, CLI `pipeline._run_source_step` line 263, tests) construct `HydrateConfig(guest_type=..., cage_occupancy_small=..., ...)` WITHOUT `cage_guest_assignments`. If Phase 42 drops/ignores the legacy fields, these break.
**Why:** The legacy fields are the existing API surface.
**How to avoid:** Keep `guest_type`, `cage_occupancy_small`, `cage_occupancy_large`, `guest_residue_name`, `guest_gro_path`, `guest_itp_path`, `guest_atom_labels`, `guest_atom_count` as-is. In `__post_init__`, if `cage_guest_assignments` is empty, synthesize it from the legacy fields (`_legacy_to_assignments()`). Existing callers continue to work; new callers pass `cage_guest_assignments` directly.
**Warning signs:** Existing tests `test_hydrate_config_metadata.py`, `test_hydrate_config_custom.py` fail.

### Pitfall 5: Thread-safety for multiple `sys.modules` registrations (GUI QThread)
**What goes wrong:** If two custom guests are registered on the worker thread (race) or cleaned up out of order, `sys.modules` can leak or shadow.
**Why:** `sys.modules` is process-global; the v4.7 decision is "register on main thread before worker starts, cleanup after it joins."
**How to avoid:** Build ALL custom-guest modules on the main thread (in `generate()` BEFORE the worker, or in the GUI's pre-thread hook). Use `ExitStack` (Pattern 3) so cleanup is guaranteed. The GUI's `register_custom_guest`/`unregister_custom_guest` pair (async path) must be called for EACH custom guest before `HydrateWorker.start()`, and each popped in the `finished` signal.
**Warning signs:** Intermittent `AssertionError: ... already registered (stale state?)` or wrong-guest-placed bugs.

### Pitfall 6: `_H` suffix uniqueness across multiple custom guests
**What goes wrong:** Two custom guests both with `guest_residue_name="MOL"` → both want `MOL_H` → GRO residue name collision (two distinct moleculetypes sharing one residue name) → grompp "molecule X not found" or silent merge.
**Why:** `validate_gro_residue_name` allows `MOL_H` (5 chars) but doesn't enforce global uniqueness.
**How to avoid:** Validate in `HydrateConfig.__post_init__` that all `guest_residue_name` values across `cage_guest_assignments` are distinct (for custom guests). If collision, either reject or auto-suffix (`MOL`, `MO2`, `MO3`...). `MoleculetypeRegistry.register_custom_molecule` already disambiguates via `_1`/`_2` counter (line 132-142) — but that's for the `_L` liquid path; the `_H` hydrate path's `register_hydrate_guest` does NOT disambiguate. **Recommendation:** enforce distinct `guest_residue_name` at config-validation time (fail fast with a clear message).
**Warning signs:** Two custom guests with the same `guest_residue_name` produce a `.gro` where both guest types have indistinguishable residues.

### Pitfall 7: `HydrateStructure` single-guest fields become stale
**What goes wrong:** `HydrateStructure` carries `guest_name`, `guest_atom_labels`, `guest_atom_count`, `guest_itp_path` (single values, lines 944-947). Downstream code (`to_candidate()` line 996-1010, `hydrate_viewer`, `interface_viewer`) reads these. For mixed occupancy, "the guest name" is ill-defined.
**Why:** The fields were designed for one guest.
**How to avoid:** Either (a) deprecate the single fields and derive from `config.cage_guest_assignments` / `molecule_index` at read-time, or (b) keep them as "the primary guest" (first non-water `mol_type`) for display + add a new `guest_descriptors: list[GuestDescriptor]` field for the full set. **Recommendation:** keep the single fields (set to the first/primary guest) for backward compat + add `guest_descriptors` for the full list. Audit downstream readers.
**Warning signs:** GUI log shows "Guest molecules: N" but doesn't break down by type; `to_candidate().metadata["guest_type_counts"]` (line 1006) already counts per-type — leverage it.

### Pitfall 8: CLI `--guest` only accepts CH4/THF (no custom-guest CLI)
**What goes wrong:** Adding mixed-occupancy CLI flags that reference a custom guest will fail because `--guest`'s `choices=["CH4","THF"]` (parser.py:217) rejects custom slugs, and the CLI `HydrateConfig` build (pipeline.py:263-271) doesn't pass `guest_gro_path`/`guest_itp_path`/`guest_residue_name`.
**Why:** Phase 40/41 added custom-guest support to the GUI path but the CLI path was never extended for custom guests (only built-in ch4/thf).
**How to avoid:** For Phase 42, decide the CLI surface. Two options: (a) CLI mixed-occupancy supports built-in guests only (ch4+thf), custom guests remain GUI-only — add `--cage-guest small=CH4:60 --cage-guest large=THF:100` with `choices` per built-in; (b) full CLI custom-guest support requires `--custom-guest-gro`/`--custom-guest-itp` flags (bigger scope). **Recommendation:** Start with (a) for Phase 42 (built-in mixed occupancy on CLI); defer (b) to a later phase. Document this as an Open Question.
**Warning signs:** CLI test for mixed ch4+thf works; CLI test for mixed ch4+custom fails with `invalid choice`.

## The sH medium cage gap — recommendation

**Recommendation: Fix the sH `cage_type_map` bug IN Phase 42 as its first prerequisite task (e.g. 42-00), NOT as a separate Phase 39 follow-up.**

**Rationale:**
1. **Phase 39 is closed** (has 39-VERIFICATION.md + all 39-XX-SUMMARY.md). Re-opening it for a 2-line fix is heavier process overhead than folding it into Phase 42.
2. **The fix is tiny:** `HYDRATE_LATTICES["sH"]["cage_type_map"]` changes from `{"small": "12", "large": "16"}` to `{"small": "12", "medium": "12_1", "large": "20"}` (2 keys changed/added in `types.py` lines 118) + 1 test update (`test_hydrate_lattice_types.py` line 79 `valid_keys`).
3. **Phase 42 cannot succeed without it:** MIXED-01 explicitly requires "sH small/medium/large". Without the fix, sH medium is unreachable (no `medium` key) and sH large silently places 0 guests (`16` is wrong). No amount of Phase 42 work can satisfy MIXED-01 for sH unless this is fixed.
4. **The bug is independently verifiable:** a regression test (`gen.generate(HydrateConfig(lattice_type="sH", guest_type="ch4", cage_occupancy_large=100.0)); assert s.guest_count > small_only_count`) fails before the fix and passes after.
5. **It's a latent bug, not a feature:** Phase 39 research flagged the correct identifiers (`12`/`12_1`/`20`, 39-RESEARCH.md line 359) but the shipped impl used `16` — so this is correcting an oversight, not expanding scope.

**Verification of the bug (ran against live env):**
```
sH small=12 only     : CH4_guests=30   (works)
sH medium=12_1 only  : CH4_guests=20   (UNREACHABLE in current code — no "medium" key)
sH large=20 only     : CH4_guests=10   (correct — but current code uses "16")
sH large=16 (current): CH4_guests=0    (BROKEN — silent zero placement)
sH all three 12+12_1+20: CH4_guests=60 (additive — confirms independent cage types)
```

**Scope guard:** the fix touches `types.py` (1 dict) + `test_hydrate_lattice_types.py` (1 `valid_keys` set + 1 new sH assertion). It does NOT touch the generator, writers, or GUI. Keep it atomic.

## Code Examples

### Verified: GenIce2 multi-guest generation (the core feasibility proof)
```python
# Source: ran against live quickice conda env (genice2 2.2.13.1) — VERIFIED
import sys, types
import numpy as np
from genice2.genice import GenIce
from genice2.plugin import safe_import
from genice2.valueparser import parse_guest
from collections import defaultdict, Counter
from quickice.structure_generation.gro_parser import parse_gro_file

# Build a synthetic etoh custom guest module (Phase 40 mechanism)
positions, atom_names, _ = parse_gro_file('quickice/data/custom/etoh.gro')
centroid = positions.mean(axis=0)
mod = types.ModuleType('genice2.molecules.etoh_mix')
code = (
    'import numpy as np\nimport genice2.molecules\n'
    'class Molecule(genice2.molecules.Molecule):\n'
    '    def __init__(self):\n'
    f'        self.sites_ = np.array({(positions - centroid).tolist()!r})\n'
    f'        self.labels_ = {list(atom_names)!r}\n'
    f'        self.name_ = "MOL"\n'
)
exec(code, mod.__dict__)
sys.modules['genice2.molecules.etoh_mix'] = mod

# sI: small=12, large=14. CH4 in small + custom etoh in large (MIXED-01/02/03).
lat = safe_import('lattice', 'sI').Lattice()
ice = GenIce(lat, reshape=np.diag([2,2,2]))
water = safe_import('molecule', 'tip4p').Molecule()
formatter = safe_import('format', 'gromacs').Format()

guests = defaultdict(dict)
parse_guest(guests, '12=ch4*1.0')        # 100% CH4 in small cages
parse_guest(guests, '14=etoh_mix*1.0')   # 100% custom etoh in large cages
gro = ice.generate_ice(formatter=formatter, water=water, guests=guests, depol='strict')

# Result (VERIFIED):
# n_atoms: 1984
# resname atom counts: {'ICE': 1472, 'CH4': 80, 'MOL': 432}
# molecule counts by residue: {'ICE': 368, 'CH4': 16, 'MOL': 48}
# → 16 CH4 (small) + 48 MOL-custom (large) coexist. MIXED OCCUPANCY WORKS NATIVELY.
sys.modules.pop('genice2.molecules.etoh_mix', None)
```

### GenIce2 `parse_guest` multi-guest semantics (valueparser.py:48-74)
```python
# Source: /share/home/nglokwan/miniconda3/envs/quickice/lib/python3.14/site-packages/genice2/valueparser.py
def parse_guest(guests, arg):
    cagetype, spec = arg.split("=")            # "12=ch4*0.6"
    contents = spec.split("+")                 # supports "ch4*0.6+etoh*0.4" (multiple in ONE cage)
    assert cagetype not in guests, "Cage type already specified."  # ← CRITICAL: no re-specifying same cage
    for content in contents:
        if "*" in content:
            molec, frac = content.split("*"); frac = float(frac)
        else:
            molec, frac = content, 1.0
        guests[cagetype][molec] = frac
    return guests
# KEY: guests is defaultdict(dict) → {"12": {"ch4": 1.0}, "14": {"etoh_mix": 1.0}}
# Different cage types → independent → MIXED-01/02/03 supported natively.
```

### sH cage types (the bug evidence)
```python
# Source: ran against live env — VERIFIED
from genice2.plugin import safe_import
lat = safe_import('lattice', 'sH').Lattice()
# lat.cages is a string (deprecated format) listing cage types + positions:
#   12         0.5000 0.5000 0.5000   ← small (5¹²)
#   12_1       0.7500 0.3333 0.7500   ← MEDIUM (4³5⁶6³) — MISSING from cage_type_map
#   20         1.0000 0.0000 0.2000   ← LARGE (5¹²6⁸) — cage_type_map wrongly says "16"
# sI cagetype:  ['12','12','14','14','14','14','14','14']  → small=12, large=14 ✓
# sII cagetype: ['12'×16, '16'×8]                            → small=12, large=16 ✓
# sH: uses deprecated `cages` string; cage ids are 12 / 12_1 / 20
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single `guest_type` + `cage_occupancy_small/large` | `cage_guest_assignments: dict[cage_key, CageGuestAssignment]` | Phase 42 (this phase) | Enables per-cage-type guest + occupancy |
| Single custom-guest `sys.modules` injection | `ExitStack` + nested `custom_guest_module` | Phase 42 | Supports ≥1 custom guest simultaneously |
| `custom_guest_info: dict \| None` (single) in writers | `custom_guest_info: list[dict] \| None` | Phase 42 | Multi-guest export |
| `create_guest_actor` → 1 actor for all guests | 1 actor per `mol_type` | Phase 42 | Per-type visual styles (MIXED-05) |
| sH `cage_type_map = {small:12, large:16}` (WRONG) | `{small:12, medium:12_1, large:20}` | Phase 42 (prereq fix) | sH medium reachable; sH large places guests |

**Deprecated/outdated:**
- `HydrateConfig.guest_type` / `cage_occupancy_small` / `cage_occupancy_large` (single-guest): kept for backward compat, but new code should use `cage_guest_assignments`. The `_legacy_to_assignments()` shim bridges them.
- `--guest` / `--cage-occupancy-small` / `--cage-occupancy-large` CLI flags: kept as deprecated aliases; new `--cage-guest` repeatable flag is the primary surface.

## Open Questions

1. **[Q1 — CLI custom-guest scope]** The CLI `--guest` only accepts CH4/THF (parser.py:217) and the CLI `HydrateConfig` build (pipeline.py:263-271) doesn't pass custom-guest metadata. **Question:** should Phase 42's CLI mixed-occupancy support (a) built-in guests only (ch4+thf mixed), or (b) full custom-guest CLI (requires `--custom-guest-gro`/`--custom-guest-itp` flags)? **Recommendation:** (a) for Phase 42 — covers MIXED-01..05 for the common case; defer (b). The CLI is already behind the GUI for custom guests (Phase 40/41 GUI-only). Planner decides. Confidence: HIGH that the gap exists; MEDIUM on the scope decision.

2. **[Q2 — `custom_guest_info` API shape]** The four writers currently take `custom_guest_info: dict | None`. **Options:** (a) change to `list[dict] | None` (breaking signature change — all call sites update); (b) add a NEW `custom_guest_infos: list[dict] | None` param and deprecate the old one; (c) a `dict[str, dict]` keyed by `mol_type`. **Recommendation:** (a) — the parameter is internal (not a public API), there are ~6 call sites, and a clean list is the simplest. Planner decides. Confidence: HIGH that (a) works; MEDIUM on the deprecation strategy.

3. **[Q3 — `render_hydrate_structure` return-type breaking change]** It currently returns `[water_actor, guest_actor]` (2-element); callers (`hydrate_viewer.py:246,397`, `interface_viewer.py:225`) index `[1]` for the guest. Returning `[water, guest1, guest2, ...]` breaks these. **Options:** (a) return a list and update callers to iterate `[1:]`; (b) return a dict `{"water": ..., "guests": [...]}`. **Recommendation:** (a) — minimal, keeps ordering. Update the 3-4 callers. Planner decides. Confidence: HIGH that the breakage is real; MEDIUM on the exact shape.

4. **[Q4 — Per-type VTK colors/styling policy]** MIXED-05 says "per-type visual styles". **Question:** should the colors be (a) a hardcoded cycle (e.g. CH4=gray, custom=cyan, ...), (b) user-configurable per cage type, or (c) derived from element CPK (current behavior — all guests use CPK, indistinguishable by type)? **Recommendation:** (a) a small palette per `mol_type` (e.g. first guest=gray, second=cyan, third=yellow) with a TODO for (b) in a later UI phase. The `per_type_colors` param in Pattern 6 supports this. Planner decides. Confidence: MEDIUM (UX decision, not technical).

5. **[Q5 — Filled-ice "guest" cage key]** Filled ices (c0te, c1te, c2te, ice1hte) have `cage_type_map = {"small": "Ne1"}` (single entry, per [39-01]). MIXED-01 mentions "filled ice channels". **Question:** should Phase 42 expose a "guest" cage key for filled ices, or keep the "small" alias? **Recommendation:** keep "small" (current) — filled ices have ONE cage type, so mixed occupancy is moot (only one assignment). Document that filled ices support per-cage occupancy but not multi-guest (only one cage). Confidence: HIGH (single cage = no mixing possible).

6. **[Q6 — `HydrateStructure` single-guest fields]** (from Pitfall 7). Keep `guest_name`/`guest_atom_labels`/`guest_atom_count`/`guest_itp_path` as "primary guest" + add `guest_descriptors: list`? Or drop them and derive? **Recommendation:** keep + add `guest_descriptors`. Audit `to_candidate()`, `hydrate_viewer`, `interface_viewer` readers. Planner decides. Confidence: MEDIUM.

## Sources

### Primary (HIGH confidence — source code read directly + code run)
- `quickice/structure_generation/hydrate_generator.py` — read full (793 lines); `_run_via_api`(200-293, single `guest_name` at 252, `parse_guest` calls at 269/277), `generate`(102-198, single `custom_guest_module` at 158), `_build_molecule_index`(556-676, single `guest_res_name` at 609)
- `quickice/structure_generation/types.py` — read full (1013 lines); `HydrateConfig`(430-571, single-guest fields 468-480, `__post_init__` 482-539, `is_custom_guest` 564), `HydrateStructure`(914-1013, single-guest fields 944-947, `to_candidate` 949-1013), `HYDRATE_LATTICES`(84-199, **sH `cage_type_map` bug at line 118**), `GUEST_MOLECULES`(203-220), `MoleculeIndex`(62-80)
- `genice2/valueparser.py` (full, 126 lines) — `parse_guest`(48-74, **assert at line 62**), confirmed dict-only, multi-cage support
- `genice2/lattices/sH` — ran `safe_import('lattice','sH').Lattice()`; confirmed cage types `12`/`12_1`/`20` via `lat.cages` string; **verified `16=ch4` places 0, `20=ch4` places 10**
- `genice2/lattices/sI`, `sII` — ran; confirmed `cagetype` arrays (sI: 12/14; sII: 12/16)
- `quickice/output/gromacs_writer.py` — read `write_multi_molecule_gro_file`(1596-1724, `custom_guest_info` at 1604, single-dict match at 1675), `write_multi_molecule_top_file`(1727-1908, `custom_guest_info` at 1733, `[molecules]` loop 1773-1807 already multi-type, atomtypes merge 1883-1889 single), `write_interface_gro_file`(1043, `custom_guest_info` 1046), `write_interface_top_file`(1442, `custom_guest_info` 1445), `_merge_custom_atomtypes`(referenced 1884)
- `quickice/structure_generation/moleculetype_registry.py` — read full (166 lines); `register_hydrate_guest`(46, no disambiguation counter), `register_custom_molecule`(96, has `_1`/`_2` disambiguation — liquid path only)
- `quickice/structure_generation/custom_guest_bridge.py` — read full (394 lines); `build_custom_guest_module`(71), `validate_custom_guest_files`(177), `custom_guest_module`(316, **assert key-absent at 346**), `register_custom_guest`(356)/`unregister_custom_guest`(382)
- `quickice/gui/hydrate_renderer.py` — read full (628 lines); `create_guest_actor`(391-484, ONE vtkMolecule for ALL non-water mols), `render_hydrate_structure`(487-507, returns `[water, guest]` 2-element), `_build_vtk_molecule_from_molecule_index`(319-388)
- `quickice/gui/vtk_utils.py` — read `interface_to_vtk_molecules`(437-676, returns `(ice, water, guest|None)` 3-tuple, single guest_mol)
- `quickice/gui/hydrate_panel.py` — read full (488 lines); single `guest_combo`(204-210), `occupancy_small`(238)/`occupancy_large`(254), `get_configuration`(434-448, single-guest `HydrateConfig`), `_update_guest_ui_for_lattice`(355-378)
- `quickice/gui/hydrate_export.py` — read full (223 lines); `export_hydrate`(90-223, single `custom_guest_info` at 163, single `itp_files` at 168, single `transform_guest_itp` at 209)
- `quickice/cli/parser.py` — read hydrate_group(194-255); `--guest` choices CH4/THF (217), `--cage-occupancy-small/large`(243-255)
- `quickice/cli/pipeline.py` — read `_build_custom_guest_info`(32-50, single dict), hydrate config build(263-271, no custom metadata), `_run_export_step`(750-859, hydrate wrapper 806-840, single `custom_guest_info` at 845)
- `tests/test_hydrate_lattice_types.py` — read(75-99); `test_cage_type_map_keys_are_small_or_large`(77, `valid_keys={"small","large"}` at 79 — **FORBIDS "medium"**)
- `tests/test_e2e_custom_guest_hydrate.py` — read(1-75); Phase 40 fixture pattern (module-scoped, unique `_GUEST_TYPE="etoh_e2e"`)
- `.planning/phases/39-extended-lattice-types/39-RESEARCH.md` — line 359 confirms sH uses `12`/`12_1`/`20` (the research flagged it)
- `.planning/phases/39-extended-lattice-types/39-01-PLAN.md` — line 71 confirms the shipped `sH: cage_type_map={"small": "12", "large": "16"}` (the bug)
- `.planning/phases/40-custom-guest-bridge-core/40-RESEARCH.md` — full (Phase 40 mechanism: sys.modules injection, name separation, centering)
- `.planning/phases/41-gromacs-export-for-custom-guests/41-RESEARCH.md` — full (Phase 41 export path, `custom_guest_info` single-dict API, P3 fix, atomtypes merge pattern)
- **POC runs** — ran two proofs-of-concept against the live `quickice` conda env (Python 3.14.3, genice2 2.2.13.1): (1) sI 2×2×2 with CH₄+custom-etoh → 16 CH₄ + 48 MOL placed (multi-guest feasibility); (2) sH cage-type comparison → `16`=0, `20`=10, `12_1`=20 (sH bug proof). Both PASS.

### Secondary (MEDIUM confidence)
- `quickice/gui/hydrate_viewer.py` — read via grep only (callers of `render_hydrate_structure` at lines 246, 397); not fully read — planner should confirm exact actor-handling when updating for variable-length actor lists (Q3)

### Tertiary (LOW confidence)
- None. All mechanism claims verified by execution; all file:line citations read directly.

## Metadata

**Confidence breakdown:**
- Standard stack (GenIce2 multi-guest capability): HIGH — verified by running a real sI+CH4+custom-etoh generation (16 CH4 + 48 MOL)
- Architecture (`cage_guest_assignments` data model + flow): HIGH — composes existing primitives; all integration points read
- sH `cage_type_map` bug: HIGH — verified `16=ch4`→0 guests, `20=ch4`→10 guests, `12_1`→20; Phase 39 research flagged the identifiers
- Generator changes (`_run_via_api` iterate, `_build_molecule_index` multi-guest): HIGH — current single-guest code read; extension is mechanical
- Export changes (writers accept list): HIGH — current single-dict code read; `[molecules]`/`#include` loops already iterate `unique_types`; only `res_name` resolution + atomtypes merge need list-awareness
- VTK per-type rendering: HIGH — `create_guest_actor` read; grouping by `mol_type` is straightforward; the breaking return-type change (Q3) is the only uncertainty
- GUI per-cage-type controls: HIGH — `HydratePanel` read; `_update_guest_ui_for_lattice` already keys off `cage_type_map`; per-cage rows are a natural extension
- CLI surface: MEDIUM — the `--cage-guest` repeatable flag design is a judgment call (Q1); custom-guest CLI is out of scope for the baseline
- sH gap recommendation (fix in Phase 42): HIGH — the bug is real, the fix is tiny, Phase 42 requires it

**Research date:** 2026-07-05
**Valid until:** 2026-08-05 (30 days — stable codebase; verify line numbers haven't shifted if Phase 41/other work commits between research and planning)

---

## Appendix A: Recommended Plan Breakdown (validate / revise the 4-task outline)

The roadmap's 4-task outline (42-01..42-04) is sound but **missing the sH prerequisite fix**. Below is a validated, revised breakdown. The revision: **add 42-00 (sH cage_type_map fix + test) as a prerequisite**, fold the data-model into 42-01, and split export/render/GUI across 42-02/03/04.

### 42-00 — Fix sH `cage_type_map` (PREREQUISITE, blocks all of Phase 42)
- `types.py` line 118: `HYDRATE_LATTICES["sH"]["cage_type_map"]` → `{"small": "12", "medium": "12_1", "large": "20"}`.
- `tests/test_hydrate_lattice_types.py` line 79: `valid_keys = {"small", "large", "medium"}` (add `"medium"`).
- Add regression test: `gen.generate(HydrateConfig(lattice_type="sH", guest_type="ch4", cage_occupancy_large=100.0))` → `assert s.guest_count > 30` (small-only is 30; with large it must be more). Also assert `cage_occupancy_small=0, cage_occupancy_large=100` → `guest_count == 10` (large-only count for 1×1×1).
- Atomic commit; no other files touched.

### 42-01 — Data model + generator (`cage_guest_assignments` + multi-guest `_run_via_api`)
- `types.py`: add `CageGuestAssignment` dataclass; add `cage_guest_assignments` to `HydrateConfig`; add `_legacy_to_assignments()` shim in `__post_init__`; validate distinct `guest_residue_name` across custom assignments (Pitfall 6); relax `__post_init__` to accept `cage_guest_assignments` as the primary input (legacy fields still accepted).
- `hydrate_generator.py::_run_via_api`: replace the single-guest small/large branch (262-277) with the loop over `cage_guest_assignments` (Pattern 2).
- `hydrate_generator.py::generate`: replace the single `custom_guest_module` context manager (136-165) with `ExitStack` + nested managers (Pattern 3).
- `hydrate_generator.py::_build_molecule_index`: replace single `guest_res_name` lookup (609) with the `resname_to_moltype` dict (Pattern 4).
- `types.py::HydrateStructure`: add `guest_descriptors: list` field (keep legacy single fields as "primary guest" for backward compat — Pitfall 7).
- Tests: `test_hydrate_config_custom.py` — `cage_guest_assignments` validation; `test_e2e_mixed_cage_occupancy.py` (NEW) — sI with ch4-small + etoh-large → assert `guest_count == 16+48` and `molecule_index` has both `ch4` and `etoh_*` mol_types. Regression: single-guest configs still work (legacy fields).

### 42-02 — Multi-guest GROMACS export (MIXED-04)
- `gromacs_writer.py`: change `custom_guest_info: dict | None` → `custom_guest_info: list[dict] | None` in all four writers (`write_multi_molecule_gro_file` 1604, `write_multi_molecule_top_file` 1733, `write_interface_gro_file` 1046, `write_interface_top_file` 1445). Update `res_name` resolution to use `custom_by_moltype` dict (Pattern 5). Loop `_merge_custom_atomtypes` over each custom ITP.
- `cli/pipeline.py::_build_custom_guest_info`: return `list[dict]` (one per custom assignment).
- `gui/hydrate_export.py::export_hydrate`: build `custom_guest_info` list + `itp_files` dict (keyed by each `mol_type`); loop `transform_guest_itp` per custom ITP; register each built-in guest in the registry.
- Tests: extend `test_e2e_custom_guest_hydrate.py` pattern to mixed ch4+etoh → export via both GUI (`export_hydrate`) and CLI (`_run_export_step`) → `gmx grompp` (use `run_gmx_grompp`) → assert `[molecules]` has `SOL` + `CH4_H` + `MOL_H`; assert `.gro` has all three residues; `assert_gro_top_consistent` passes.

### 42-03 — Per-type VTK rendering (MIXED-05)
- `hydrate_renderer.py::create_guest_actor`: group by `mol_type` (excluding water); build one `vtkMolecule` per group; return `list[vtkActor]` (Pattern 6).
- `hydrate_renderer.py::render_hydrate_structure`: return `[water_actor, *guest_actors]` (variable length).
- `hydrate_viewer.py` (lines 246, 397) + `interface_viewer.py` (line 225): update to handle variable-length actor lists (iterate `[1:]` for guests; store per-type for visibility toggles).
- Tests: `test_custom_molecule_renderer.py` pattern — assert mixed structure renders N+1 actors (1 water + N guest types); per-type visibility toggle works.

### 42-04 — GUI per-cage-type controls + CLI surface
- `hydrate_panel.py`: replace `_create_guest_group` + `_create_occupancy_group` (198-269) with a **per-cage-type row** built from `HYDRATE_LATTICES[lat]["cage_type_map"]` keys. For each key: a `QComboBox` (built-in ch4/thf + custom-guest upload button) + a `QDoubleSpinBox` (occupancy). Rebuild rows on `lattice_combo` change (extend `_update_guest_ui_for_lattice`).
- `hydrate_panel.py::get_configuration`: build `HydrateConfig(cage_guest_assignments={...})` from the per-cage rows (instead of legacy single fields).
- `cli/parser.py`: add `--cage-guest` repeatable (`action="append"`, format `key=guest:occ` e.g. `--cage-guest small=CH4:60 --cage-guest large=THF:100`). Keep `--guest`/`--cage-occupancy-small/large` as deprecated aliases (Q1 option a — built-in only on CLI).
- `cli/pipeline.py`: build `HydrateConfig(cage_guest_assignments=...)` from `args.cage_guest` (fallback to legacy fields).
- Tests: GUI — per-cage rows appear/disappear with lattice; config round-trips. CLI — `--cage-guest small=CH4:60 large=THF:100` → `HydrateConfig.cage_guest_assignments` has 2 entries; generation places both; `--guest` legacy still works.

### Cross-cutting
- AGENTS.md constraints: atomic commits (one task per commit); specific exceptions in `pipeline.py` (no bare `except Exception`); no hardcoded TIP4P-ICE/`0.0299`/`4` (use constants); `@gmx_skipif` on grompp tests; `QT_QPA_PLATFORM=offscreen` for GUI tests; `_H` suffix + comb-rule=2 (no auto-conversion).
- The sH fix (42-00) MUST land first — 42-01's mixed-occupancy tests for sH will fail without it.
