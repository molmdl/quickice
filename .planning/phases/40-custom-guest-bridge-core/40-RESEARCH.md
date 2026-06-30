# Phase 40: Custom Guest Bridge Core - Research

**Researched:** 2026-06-30
**Domain:** GenIce2 plugin injection, GROMACS ITP/GRO parsing, thread-safe module registration
**Confidence:** HIGH (mechanism verified by running proof-of-concept code against the live `quickice` conda env)

## Summary

Phase 40 adds the ability to upload a custom guest molecule (`.gro` + `.itp` pair) and have it placed in hydrate cage positions via GenIce2. The core technical mechanism — **injecting a synthetic `ModuleType` into `sys.modules` so GenIce2's `safe_import('molecule', <name>)` finds it** — was verified end-to-end by running a proof-of-concept that generated an sI hydrate with a custom ethanol guest (2 ETOH molecules placed in large cages). This confirms the approach documented in PROJECT.md ("verified end-to-end with CS1+ethanol").

GenIce2's `safe_import` calls `importlib.import_module(...)`, which **returns the cached entry from `sys.modules` without re-importing** (verified). A plugin module needs only a `Molecule` class exposing `sites_` (N×3 positions **relative to the molecule center**, in nm), `labels_` (atom names), and `name_` (residue name). No `desc` dict is required for generation (only for plugin discovery/listing). The molecule **must be centered** (centroid subtracted) because GenIce2's `arrange()` adds the cage-center position to `sites_`; it does not center for you.

The cleanest architecture separates two distinct names: **`guest_type`** (the GenIce2 plugin name / `sys.modules` key, a slugified unique identifier matching `^[A-Za-z0-9-_]+$`, can be >3 chars) and **`guest_residue_name`** (the GRO residue name, ≤3 chars base so the `_H` suffix yields ≤5 chars). A new `guest_residue_name` field on `HydrateConfig` is recommended so `_build_molecule_index` can robustly identify custom guests by residue grouping (the atom-label-matching fallback already works but is fragile when a guest's first atom collides with water atoms).

Validation requires **adding a comb-rule parser** — no `[ defaults ]`/comb-rule parsing exists anywhere in the codebase today. Comb-rule lives in the `[ defaults ]` section (present in `.top`, sometimes in `.itp`); Phase 40 must parse the `.itp` for `[ defaults ]` and reject `comb-rule=1`. Test data `etoh.itp` has no `[ defaults ]` (it's in `etoh.top`), so absence must be accepted (QuickIce's main `.top` uses comb-rule=2).

**Primary recommendation:** Build `quickice/structure_generation/custom_guest_bridge.py` with three responsibilities — (1) parse+validate GRO/ITP, (2) build+center the synthetic `Molecule` module and register it in `sys.modules` under `genice2.molecules.<guest_type>`, (3) provide a cleanup primitive. Wire it into `HydrateStructureGenerator._run_via_api` (or a pre-step) so `guest_type="custom"` flows through. Add `guest_residue_name` to `HydrateConfig` and relax `__post_init__` to accept custom guest types. Do NOT auto-convert Å→nm (GRO spec is nm; rely on the existing >50nm rejection).

## Standard Stack

### Core (existing — REUSE, do not reinvent)
| Library / Module | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `genice2` | 2.2.13.1 | Hydrate lattice + guest placement | The whole phase exists to bridge into it |
| `genice2.plugin.safe_import` | — | Loads molecule plugins (checks `sys.modules` first) | THE injection point (verified) |
| `genice2.valueparser.parse_guest` | — | Builds `guests` dict from `"cage=mol*frac"` spec | Does NOT call safe_import; just dict-building |
| `genice2.molecules.Molecule` (base) | — | Base class: `sites_`, `labels_`, `name_`, `get()` | Synthetic module subclasses this |
| `quickice...gro_parser` | existing | `parse_gro_file`/`parse_gro_string` → (positions, atom_names, cell); rejects >50nm | Already validates Å-mixup; reuse as-is |
| `quickice...itp_parser` | existing | `parse_itp_file` → `ITPMoleculeInfo` (name, atom_types, atom_names, charges, has_atomtypes) | Reuse; **lacks comb-rule** (must extend) |
| `quickice...moleculetype_registry` | existing | `register_hydrate_guest` → `{name}_H`; `RESERVED_NAMES` | Reuse for `_H` suffix naming |
| `quickice.output.gromacs_writer.transform_guest_itp` | existing | Comments out `[ atomtypes ]`, rewrites `[ moleculetype ]` name with `_H` | Reuse; **needs `[ atoms ]` resname rewrite added** (Phase 40) |
| `quickice...molecule_validator` | existing | `validate_custom_molecule` (liquid path) — GRO/ITP consistency | Pattern to mirror; does NOT check comb-rule or name length |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `numpy` | — | `sites_` array, centroid subtraction | Always |
| `types.ModuleType` | stdlib | Synthetic plugin module | The injected module object |
| `importlib.import_module` | stdlib | Confirms `sys.modules` cache precedence | Understanding only; GenIce2 calls it for us |
| `threading` | stdlib | Import lock awareness; main-thread injection discipline | Thread-safety |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `sys.modules["genice2.molecules.<name>"]` injection | `sys.modules["molecules.<name>"]` (local namespace, tried first by `safe_import`) | Both verified working; `genice2.molecules.*` namespace is clearer and avoids hijacking the `molecules.*` local-search path. **Use `genice2.molecules.*`.** |
| `sys.modules` injection | Writing a real `.py` plugin into GenIce2's `__path__` or `~/.genice/molecules/` | Requires filesystem write + cleanup; fragile across installs/envs. sys.modules injection is ephemeral and thread-controllable. **Use sys.modules.** |
| New `guest_residue_name` field | Make `guest_type` BE the residue name (≤3 chars) | Collides with built-ins (e.g., user residue "CH4" shadows `genice2.molecules.ch4`); forces ≤3-char plugin names. Separate field decouples cleanly. **Use separate field.** |
| Auto-convert Å→nm | Reject / assume nm | GRO spec is nm; auto-detect is unreliable for small molecules (a 2.0 Å value passes the >50nm check but is 10× wrong). **No auto-convert; rely on existing >50nm rejection.** |

**Installation:**
```bash
# No new dependencies. Uses only stdlib + existing quickice modules + genice2 (already installed).
# Do NOT add anything to environment.yml for this phase.
```

## Architecture Patterns

### Recommended Project Structure
```
quickice/structure_generation/
├── custom_guest_bridge.py     # NEW (Phase 40): parse+validate+build+register+cleanup
├── hydrate_generator.py       # MODIFY: _run_via_api uses custom guest; _build_molecule_index uses guest_residue_name
├── types.py                   # MODIFY: HydrateConfig gains guest_residue_name; relax __post_init__
├── itp_parser.py              # MODIFY: add comb-rule / [ defaults ] extraction (extend ITPMoleculeInfo)
├── gro_parser.py              # REUSE as-is
├── moleculetype_registry.py   # REUSE as-is (register_hydrate_guest)
└── molecule_validator.py      # REUSE pattern; add hydrate-guest validator (or fold into bridge)
quickice/data/custom/
├── etoh.gro / etoh.itp / etoh.top   # VALID test fixture (9 atoms, residue "MOL", nm)
└── test_invalid/                    # INVALID fixtures (mismatch, not_gro, no_atomtypes, na_single)
```

### Pattern 1: Synthetic GenIce2 Molecule Plugin via sys.modules
**What:** Build a `types.ModuleType` with a `Molecule` class and inject it into `sys.modules["genice2.molecules.<guest_type>"]` so GenIce2's `safe_import('molecule', <guest_type>)` returns it.
**When to use:** Always, for custom guests. Built-in guests (ch4, thf) are loaded normally.
**Why it works:** `importlib.import_module` checks `sys.modules` first and returns the cached object without re-importing (verified). `safe_import` (genice2/plugin.py:244) tries `importlib.import_module("genice2.molecules.<name>")` as its second attempt — the injected key matches.

**Verified proof-of-concept** (ran against live env; full file at `/tmp/opencode/poc_custom_guest.py`):
```python
import sys, types
import numpy as np
from quickice.structure_generation.gro_parser import parse_gro_file

def build_and_register(gro_path, guest_type, residue_name):
    positions, atom_names, _ = parse_gro_file(gro_path)          # nm, validates >50nm
    centroid = positions.mean(axis=0)
    centered = positions - centroid                                # GenIce2 adds cage center
    mod_key = f"genice2.molecules.{guest_type}"
    mod = types.ModuleType(mod_key)
    # A docstring on Molecule is nice (Stage7 logs gmol.__doc__) but desc dict is NOT required.
    code = (
        "import numpy as np\nimport genice2.molecules\n"
        f"class Molecule(genice2.molecules.Molecule):\n"
        f"    '''Custom guest {residue_name}.'''\n"
        "    def __init__(self):\n"
        f"        self.sites_ = np.array({centered.tolist()!r})\n"
        f"        self.labels_ = {list(atom_names)!r}\n"
        f"        self.name_ = {residue_name!r}\n"
    )
    exec(code, mod.__dict__)
    sys.modules[mod_key] = mod
    return mod_key

# VERIFY: safe_import finds it
from genice2.plugin import safe_import, audit_name
assert audit_name(guest_type)          # ^[A-Za-z0-9-_]+$  (no dots/spaces/slashes)
loaded = safe_import("molecule", guest_type)
assert loaded is sys.modules[mod_key]  # returned the cached module
mol = loaded.Molecule()
name, labels, sites = mol.get()        # (name_, labels_, sites_)
```

**End-to-end generation (verified):**
```python
from genice2.genice import GenIce
from genice2.valueparser import parse_guest
from collections import defaultdict
lattice = safe_import("lattice", "sI").Lattice()
ice = GenIce(lattice, reshape=np.diag([1,1,1]))
water = safe_import("molecule", "tip4p").Molecule()
formatter = safe_import("format", "gromacs").Format()
guests = defaultdict(dict)
parse_guest(guests, "12=etohguest")          # "12" = sI SMALL cage (5¹²); dict-building only
gro_string = ice.generate_ice(formatter=formatter, water=water, guests=guests, depol="strict")
# → 202 atoms; residues {'ICE','ETOH'}; 2 ETOH molecules (18 atoms) placed in sI's 2 small cages. PASS.
# (sI cage_type_map = {small:'12', large:'14'}; use "14=..." to target large cages.)
```

### Pattern 2: Thread-safe registration (main-thread injection, post-run cleanup)
**What:** Register in `sys.modules` on the **main thread before HydrateWorker starts**; remove it **after the worker finishes**.
**When to use:** GUI (QThread) and CLI (synchronous).
**Why:** `sys.modules` is a process-global dict. `importlib` briefly holds the import lock, but the real hazard is **concurrent modification** (one thread writing the key while another reads/imports). Doing the write before the worker exists and the delete after it joins eliminates the race window (v4.7 decision).

**Core primitives (CLI/synchronous uses a context manager; GUI uses register/unregister pair):**
```python
import sys, types
from contextlib import contextmanager

@contextmanager
def custom_guest_module(guest_type: str, module: types.ModuleType):
    """Register a custom guest module in sys.modules for the duration of the block.

    Call on the main thread. Cleanup always runs (try/finally).
    """
    key = f"genice2.molecules.{guest_type}"
    assert key not in sys.modules, f"{key} already registered (stale state?)"
    sys.modules[key] = module
    try:
        yield key
    finally:
        sys.modules.pop(key, None)   # safe even if absent

# GUI async equivalent:
def register_custom_guest(guest_type, module):   # call BEFORE thread.start()
    sys.modules[f"genice2.molecules.{guest_type}"] = module
def unregister_custom_guest(guest_type):          # call in thread 'finished' signal
    sys.modules.pop(f"genice2.molecules.{guest_type}", None)
```

### Pattern 3: Name separation (guest_type vs guest_residue_name)
**What:** Two distinct identifiers per custom guest:
- `guest_type` — GenIce2 plugin name + `sys.modules` key + `safe_import` arg. Slugified, unique, matches `^[A-Za-z0-9-_]+$`. May exceed 3 chars. (e.g. `"etoh_custom"`)
- `guest_residue_name` — the GRO residue name (`Molecule.name_`). Base ≤3 chars so `{name}_H` ≤5 chars (GRO fixed-width limit). (e.g. `"MOL"`)

**When:** Always for custom guests. Built-ins keep `guest_type` ≡ lowercased residue name (ch4→CH4).

### Anti-Patterns to Avoid
- **Auto-converting Å→nm:** GRO spec is nm. A 2.0 Å value passes the >50 nm guard but is 10× wrong. Do not guess units; assume nm and reject gross errors via the existing `parse_gro_string` >50 nm check.
- **Injecting under the user's raw residue name as plugin name:** e.g. residue "CH4" would shadow `genice2.molecules.ch4`. Use a namespaced/unique `guest_type`.
- **Building the `Molecule` module on the worker thread:** risks racing `sys.modules` writes. Build+register on main thread.
- **Skipping cleanup:** leaves stale entries that shadow built-ins on the next generation. Always `finally: sys.modules.pop(key, None)`.
- **Relying solely on atom-label matching for `_build_molecule_index`:** works for ethanol (first atom "H" doesn't collide with water OW/HW1/HW2/MW) but is fragile for guests whose first atom is "O" (collides with 3-site water). Use residue grouping (preferred) via `guest_residue_name`.
- **Bare `except Exception`** in the bridge (AGENTS.md forbids it in core pipeline code). Use `except (ValueError, OSError, KeyError)` etc.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| GRO parsing | regex/line-splitter | `quickice...gro_parser.parse_gro_file` | Already validates >50nm Å-mixup, handles triclinic cells |
| ITP parsing | custom section walker | `quickice...itp_parser.parse_itp_file` | Already extracts moleculetype, atom_types, atom_names, charges, has_atomtypes |
| `_H` suffix naming | string concat | `MoleculetypeRegistry.register_hydrate_guest` | Reserved-name collision checks, consistent _H/_L convention |
| ITP transform (atomtypes comment-out, moleculetype rename) | new function | `transform_guest_itp` (extend for `[ atoms ]` resname) | Phase 38-04 already scaffolded this; just add the deferred `[ atoms ]` rewrite |
| GenIce2 molecule interface | custom placement math | subclass `genice2.molecules.Molecule` with `sites_`/`labels_`/`name_` | GenIce2's `arrange()` handles rotation+cage placement; we only supply geometry |
| Cage→guest occupancy spec | custom dict builder | `genice2.valueparser.parse_guest` | Already parses `"cage=mol*frac"`; matches existing `_run_via_api` usage |

**Key insight:** The only genuinely NEW machinery is (a) the synthetic-module builder, (b) the comb-rule parser, (c) the `[ atoms ]` resname rewriter, and (d) the `guest_residue_name` plumbing. Everything else composes existing pieces.

## Common Pitfalls

### Pitfall 1: Forgetting to center the molecule
**What goes wrong:** GenIce2 places the molecule's centroid OFF the cage center; guests poke through cage walls.
**Why:** `genice2.molecules.arrange()` computes `abscom + (sites_ @ rotation)` where `abscom` is the cage center. It treats `sites_` as **relative** coordinates. The base `Molecule.__init__` even comments: "sites: positions of interaction sites relative to a center of molecule".
**How to avoid:** `sites_ = positions - positions.mean(axis=0)`. Verified the ch4/thf plugins do this (ch4 sites are symmetric about origin; thf divides by 10 AND is centered).
**Warning signs:** Guests appear shifted/clustered to one side of cages; "Too many guests" assertion or distorted geometry in output.

### Pitfall 2: Residue-name mismatch breaks `_build_molecule_index`
**What goes wrong:** Custom guest atoms get tracked as "unknown" molecules (or mis-identified) → wrong guest_count, broken export.
**Why:** `_build_molecule_index` does `guest_res_name = config.guest_type.upper()` then matches `residue == guest_res_name`. For a custom guest, `guest_type` (e.g. "etoh_custom") ≠ the GenIce2 output residue (`Molecule.name_`, e.g. "MOL"). Residue grouping silently fails. (Atom-label matching can rescue it — verified for ethanol — but is fragile.)
**How to avoid:** Add `guest_residue_name` to `HydrateConfig`; set `Molecule.name_ = guest_residue_name`; use `guest_residue_name` (falling back to `guest_type.upper()`) in `_build_molecule_index`.
**Warning signs:** `mol_types` contains "unknown" for a valid custom guest; `guest_count` is 0 or wrong.

### Pitfall 3: `audit_name` rejects the plugin name
**What goes wrong:** `safe_import` asserts `audit_name(name)` fails → `AssertionError: Dubious molecule name`.
**Why:** `audit_name` requires `^[A-Za-z0-9-_]+$`. Names with dots (`.gro`), spaces, slashes are rejected.
**How to avoid:** Slugify `guest_type`: strip extension, replace non-`[A-Za-z0-9-_]` with `_`, lowercase. Validate before injection. (Verified "etoh", "etoh_custom", "my-mol" pass; "etoh.gro", "my mol" fail.)

### Pitfall 4: comb-rule is NOT in the .itp (it's in the .top)
**What goes wrong:** Either can't validate comb-rule (looks in wrong file) or wrongly rejects every valid .itp.
**Why:** GROMACS `[ defaults ]` (which holds comb-rule) conventionally lives in the main `.top`, not the `.itp`. Test fixture `etoh.itp` has NO `[ defaults ]`; `etoh.top` does (`1 2 yes 0.5 0.8333`).
**How to avoid:** Parse the `.itp` for `[ defaults ]`; **reject only if present AND comb-rule ≠ 2**; **accept if absent** (QuickIce's generated main `.top` always uses comb-rule=2 — see gromacs_writer.py defaults lines). For thoroughness, optionally also accept the `.top` if provided.
**Warning signs:** Every uploaded molecule rejected with "comb-rule=1" even though the user's file is standard.

### Pitfall 5: Stale sys.modules entry on exception
**What goes wrong:** A failed generation leaves `genice2.molecules.<name>` in `sys.modules`; the next run shadows/breaks or a re-upload silently uses the old module.
**Why:** Forgetting `finally` cleanup, or cleanup placed after a raising statement.
**How to avoid:** Always use `try/finally` (context manager) or register/unregister pair with the unregister in the QThread `finished` signal. `sys.modules.pop(key, None)` is safe if absent.

### Pitfall 6: Shadowing a built-in plugin name
**What goes wrong:** If `guest_type` equals a built-in ("ch4","thf","tip4p"), the injected module shadows the real one for the duration of generation.
**Why:** `safe_import` returns the `sys.modules` cached entry first.
**How to avoid:** Namespace custom `guest_type` (e.g. prefix `custom_` or derive from a counter/UUID-ish slug). Never inject under a bare built-in name.

### Pitfall 7: `[ atoms ]` resname not rewritten to match `_H` moleculetype
**What goes wrong:** GROMACS `.itp` has `[ moleculetype ] etoh_custom_H` but `[ atoms ]` still says `MOL`. grompp does not strictly require them to match, but it's inconsistent and confuses downstream tools/inspection; the deferred Phase 38-04 item explicitly assigns `[ atoms ]` resname rewriting to Phase 40.
**How to avoid:** Extend `transform_guest_itp` (or add `rewrite_atoms_resname`) to replace the resname column in `[ atoms ]` lines with the `{residue_name}_H` value for custom guests.

## Code Examples

### GenIce2 Molecule base interface (verified — genice2/molecules/__init__.py)
```python
class Molecule():
    def __init__(self, **kwargs):
        assert len(kwargs) == 0
        self.sites_ = np.zeros([1, 3])   # (N,3) positions RELATIVE to center, in nm
        self.labels_ = ["Me", ]          # atom labels
        self.name_ = "MET"               # residue name (GROMACS) — becomes GRO residue
    def get(self):
        return self.name_, self.labels_, self.sites_
```
Source: `/share/home/nglokwan/miniconda3/envs/quickice/lib/python3.14/site-packages/genice2/molecules/__init__.py`

### How GenIce2 places a guest (genice2/molecules/__init__.py:arrange, genice.py:Stage7)
```python
# Stage7 (genice.py:1112-1125)
for molec, cages in molecules.items():
    guest_type, guest_options = plugin_option_parser(molec)
    gmol = safe_import("molecule", guest_type).Molecule(**guest_options)  # <-- injection point
    cage_center = [self.repcagepos[i] for i in cages]
    cmat = [np.identity(3) for i in cages]
    self.universe.append(arrange(cage_center, self.repcell, cmat, gmol))

# arrange() (molecules/__init__.py:8-25)
name, labels, intra = molecule.get()        # intra == sites_ (centered, nm)
for order, pos in enumerate(coord):          # coord == cage centers
    abscom = cell.rel2abs(pos)               # cage center in absolute coords
    rotated = intra @ rotmatrices[order]     # rotate the (centered) molecule
    mols.positions.append(abscom + rotated)  # place at cage center
```
**Implication:** `sites_` MUST be centered. Confirmed by running: un-centered ethanol would be offset by its centroid (~0.027 nm) from the cage center.

### safe_import resolution order (genice2/plugin.py:244-298)
```python
def safe_import(category, name):
    assert audit_name(name), f"Dubious {category} name: {name}"   # ^[A-Za-z0-9-_]+$
    module = None
    # 1. local:  importlib.import_module(f"{category}s.{name}")        e.g. "molecules.etoh"
    # 2. system: importlib.import_module(f"genice2.{category}s.{name}") e.g. "genice2.molecules.etoh"
    # 3. extra:  entry_points(group=f"genice2_{category}")
    ...
```
`importlib.import_module` returns the `sys.modules` cached entry first — **verified** (`r is mod` → True).

### parse_guest is dict-only (genice2/valueparser.py:48-74)
```python
def parse_guest(guests, arg):
    cagetype, spec = arg.split("=")     # "12=etoh_custom*0.5"
    for content in spec.split("+"):    # supports multi: "a+b"
        if "*" in content:
            molec, frac = content.split("*"); frac = float(frac)
        else:
            molec, frac = content, 1.0
        guests[cagetype][molec] = frac
    return guests
# Does NOT call safe_import. Stage7 does, later, using `molec` as the plugin name.
```

### Comb-rule parser (NEW — to add to itp_parser.py)
```python
import re

def parse_itp_defaults_comb_rule(content: str) -> int | None:
    """Return comb-rule from an ITP/TOP [ defaults ] section, or None if absent.

    [ defaults ]
    ; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
         1        2         yes       0.5     0.8333
    """
    m = re.search(r'\[\s*defaults\s*\](.*?)(?=\[\s*\w+\s*\]|$)', content, re.DOTALL | re.IGNORECASE)
    if not m:
        return None
    for line in m.group(1).splitlines():
        s = line.strip()
        if not s or s.startswith(';') or s.startswith('#'):
            continue
        fields = s.split()
        # fields: [nbfunc, comb-rule, gen-pairs, fudgeLJ, fudgeQQ]
        if len(fields) >= 2:
            try:
                return int(fields[1])
            except ValueError:
                return None
    return None

# Validation rule:
#   comb = parse_itp_defaults_comb_rule(itp_content)
#   if comb is not None and comb != 2:
#       raise ValueError("ITP comb-rule must be 2 (Lorentz-Berthelot); got comb-rule={comb}. ...")
#   # comb is None => accept (main .top will supply comb-rule=2)
```

### Validation checklist (order matters — validate BEFORE injection)
```python
# 1. GRO parseable (atom names + positions, nm)
positions, atom_names, _ = parse_gro_file(gro_path)   # raises ValueError if >50nm

# 2. ITP parseable (moleculetype name, atom types, charges)
itp_info = parse_itp_file(itp_path)                    # raises ValueError if missing [ moleculetype ]/[ atoms ]

# 3. Atom counts match between GRO and ITP
if len(positions) != itp_info.atom_count:
    raise ValueError(f"Atom count mismatch: GRO={len(positions)}, ITP={itp_info.atom_count}")

# 4. Residue name <=3 chars (base, before _H suffix => final <=5 chars)
gro_resname = extract_residue_name_from_gro(gro_path)   # columns 6-10
if gro_resname and len(gro_resname) > 3:
    raise ValueError(
        f"Custom guest residue name '{gro_resname}' ({len(gro_resname)} chars) exceeds 3 chars. "
        f"GRO format allows 5-char residue names; QuickIce reserves 2 chars for the '_H' hydrate suffix. "
        f"Use a residue name of 3 chars or fewer (e.g. 'MOL')."
    )

# 5. comb-rule == 2 (if [ defaults ] present in ITP)
comb = parse_itp_defaults_comb_rule(itp_path.read_text())
if comb is not None and comb != 2:
    raise ValueError(
        f"ITP comb-rule must be 2 (Lorentz-Berthelot / AMBER-GAFF2); got comb-rule={comb}. "
        f"QuickIce does not auto-convert A/B rules. Please regenerate the ITP with comb-rule=2."
    )

# 6. [ atomtypes ] present (warn, not block — main .top may define them)
if not itp_info.has_atomtypes_section:
    logger.warning("No [ atomtypes ] in ITP; ensure types are defined in the main .top")

# 7. audit_name(guest_type) — slugified plugin name
if not audit_name(guest_type):
    raise ValueError(f"Invalid guest type name '{guest_type}'; allowed chars: A-Z a-z 0-9 _ -")
```

### Integration into HydrateStructureGenerator._run_via_api
The current code (hydrate_generator.py:198-233) maps `guest_type` → GenIce2 name and calls `parse_guest(guests, f"{cage}={guest_name}*{occ}")`. For custom guests, `guest_name = guest_type` (the else branch already passes it through). **No change needed to the parse_guest call** — the only requirement is that `sys.modules["genice2.molecules.<guest_type>"]` is populated BEFORE `ice.generate_ice(...)` runs. So the bridge registers on the main thread, `generate()` is called, then cleanup.

```python
# In generate() or a pre-step, BEFORE _run_via_api:
if config.is_custom_guest:                       # NEW flag / guest_type not in GUEST_MOLECULES
    module = build_custom_guest_module(config)   # parse+validate+center+build ModuleType
    with custom_guest_module(config.guest_type, module):   # registers in sys.modules
        return self._run_via_api(lattice_name, config)     # generate_ice finds it via safe_import
# (cleanup runs on exit via context manager)
```

### _build_molecule_index change (minimal, robust)
```python
# hydrate_generator.py, metadata-driven path
guest_type = config.guest_type
# NEW: prefer explicit residue name for custom guests; fall back to guest_type.upper()
guest_res_name = getattr(config, "guest_residue_name", "") or guest_type.upper()
guest_signature = guest_atom_labels[0] if guest_atom_labels else None
# ... existing residue-grouping & atom-label logic unchanged, now uses guest_res_name
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pattern-matching `_build_molecule_index` (hardcoded "Me","THF") | Metadata-driven (config.guest_atom_labels, guest_type) | Phase 38-01 | Enables custom guests without code changes per type |
| `shutil.copy` for guest ITPs at export | `read → transform_guest_itp → write` | Phase 38-04 | Applies `_H` suffix + atomtypes comment-out; ready for custom ITPs |
| No GRO residue-name length check | `validate_gro_residue_name` rejects >5 chars at write time | Phase 38-03 | Prevents silent fixed-width corruption |
| ITP `[ atoms ]` resname not rewritten | (deferred to Phase 40) | — | Phase 40 must add the rewrite for custom guests |

**Deprecated/outdated:**
- Treating `guest_type` as identical to the residue name: fine for built-ins (ch4↔CH4) but breaks for custom guests where the plugin slug and the ≤3-char residue name diverge. Use `guest_residue_name`.

## Open Questions

1. **Should Phase 40 also accept an optional `.top` for comb-rule validation?**
   - What we know: `etoh.itp` has no `[ defaults ]`; `etoh.top` does (comb-rule=2). GUEST-07 says "reject ITP files with comb-rule=1".
   - What's unclear: whether the GUI will offer a `.top` upload or only `.gro`+`.itp`.
   - Recommendation: Parse `.itp` for `[ defaults ]` (reject comb-rule=1 if present; accept if absent). Optionally also parse an uploaded `.top` if provided in Phase 44/45 UI. This satisfies GUEST-07 without mandating a `.top`. Flag for planner: create a test fixture `.itp` containing `[ defaults ]` with comb-rule=1 to exercise the reject path (none exists today).

2. **`guest_type` uniqueness across a session (multiple custom guests)?**
   - What we know: A single `sys.modules` key per generation. `MoleculetypeRegistry.register_custom_molecule` already disambiguates collisions ("MOL" → "MOL_1").
   - What's unclear: Whether v4.7 needs >1 custom guest simultaneously (mixed occupancy Phase 42).
   - Recommendation: For Phase 40, one custom guest per generation is sufficient (matches the single `guest_type` field). Mixed occupancy (Phase 42) will extend this. Slugify `guest_type` to be unique (e.g. include a short hash/counter) to avoid shadowing.

3. **Does grompp require `[ atoms ]` resname to equal `[ moleculetype ]` name?**
   - What we know: grompp does NOT strictly enforce this (resname is informational); but the Phase 38-04 deferral explicitly assigns the rewrite to Phase 40.
   - Recommendation: Rewrite `[ atoms ]` resname → `{residue_name}_H` for consistency and to honor the deferred plan item. Mark as MEDIUM confidence (GROMACS behavior from training, not re-verified against current grompp this session).

4. **Cage-type selection (GUEST-02) — is it already handled?**
   - What we know: `_run_via_api` already routes guests to small/large cages via `cage_type_map` from `HYDRATE_LATTICES` and `cage_occupancy_small`/`cage_occupancy_large`. So a custom guest set as `guest_type` with occupancy on "large" already places it in large cages.
   - What's unclear: "medium" cages (sH has a medium cage) — `cage_type_map` currently has small/large keys (Phase 39). Medium may need adding.
   - Recommendation: Phase 40 (core) reuses the existing occupancy routing; GUEST-02 "selection" is a UI concern (Phase 44). **Verified gap:** `HYDRATE_LATTICES["sH"]["cages"]` has keys `['small','medium','large']` but `cage_type_map` only has `{'small':'12','large':'16'}` — **no 'medium' key**. So sH medium cages are not currently routable. This is a **Phase 39 follow-up** (lattice types), not Phase 40. Phase 40 should target whichever cage types `cage_type_map` exposes (small/large) and document that medium requires the Phase 39 fix.

## Sources

### Primary (HIGH confidence — verified by running code)
- `genice2/plugin.py` (safe_import, audit_name, import_extra) — read in full; injection mechanism confirmed
- `genice2/valueparser.py` (parse_guest) — confirmed dict-only, no safe_import call
- `genice2/molecules/__init__.py` (Molecule base, arrange) — confirmed sites_ are relative-to-center
- `genice2/genice.py` Stage7 (lines 1020-1136) — confirmed `safe_import("molecule", guest_type).Molecule(...)` is the injection point during `generate_ice`
- `quickice/structure_generation/gro_parser.py`, `itp_parser.py`, `hydrate_generator.py`, `moleculetype_registry.py`, `molecule_validator.py`, `types.py` — read in full
- `quickice/output/gromacs_writer.py` (transform_guest_itp, validate_gro_residue_name, write_multi_molecule_gro_file registry usage) — read
- Proof-of-concept runs (`/tmp/opencode/poc_custom_guest.py`, `poc2_molecule_index.py`) — all assertions passed against the live `quickice` conda env (Python 3.14.3, genice2 2.2.13.1)

### Secondary (MEDIUM confidence)
- PROJECT.md / ROADMAP.md / REQUIREMENTS.md — v4.7 decisions (sys.modules injection, _H suffix, reject A/B auto-conversion, 5-char limit)
- GROMACS `[ atoms ]`/`[ moleculetype ]` resname relationship — from training knowledge (grompp does not strictly enforce match); flagged in Open Questions #3

### Tertiary (LOW confidence)
- None. All mechanism claims verified by execution.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all modules read in source; GenIce2 mechanism verified by running POC
- Architecture (sys.modules injection + centering + name separation): HIGH — POC generated a real sI+ethanol hydrate
- Validation (comb-rule, name length, counts): HIGH for parse/count/name; MEDIUM for comb-rule-in-ITP-only assumption (test data has it in .top; design accepts absent [ defaults ])
- Integration points: HIGH — read hydrate_generator, types, gromacs_writer, cli/itp_helpers
- Thread-safety: MEDIUM — pattern is sound (main-thread write, post-run delete) but not stress-tested under concurrent QThreads this session; relies on documented v4.7 decision

**Research date:** 2026-06-30
**Valid until:** 2026-07-30 (30 days; stable domain — no fast-moving deps introduced)

---

## Appendix A: Recommended Plan Breakdown (validate / revise the 4-task outline)

The roadmap's 4-task outline is sound. Below is a validated, slightly revised breakdown with concrete deliverables and test anchors. The revision: fold "centering + units" into 40-01 (not a separate concern) and split validation into 40-03; the residue-name & `[ atoms ]` rewrite is small enough to live in 40-04 (integration) or 40-03 (validation/transform).

### 40-01 — Build `custom_guest_bridge.py` (GRO→Molecule conversion, centering, validation core)
- New module `quickice/structure_generation/custom_guest_bridge.py`:
  - `build_custom_guest_module(gro_path, guest_type, residue_name) -> types.ModuleType` — parse GRO (reuse `parse_gro_file`), **center** (subtract centroid), build `Molecule` subclass module (sites_, labels_, name_).
  - `validate_custom_guest(gro_path, itp_path) -> CustomGuestValidation` — reuse `parse_gro_file` + `parse_itp_file`; check atom-count match, residue name ≤3 chars, `[ atomtypes ]` presence (warn), audit_name(guest_type).
  - **Add comb-rule parser** to `itp_parser.py` (`parse_itp_defaults_comb_rule` / extend `ITPMoleculeInfo`) and reject comb-rule=1 when `[ defaults ]` present.
- Unit tests: valid etoh passes; `etoh_mismatch.gro` rejected (count); `not_a_gro.txt` rejected; residue >3 chars rejected; comb-rule=1 rejected (needs a NEW fixture `.itp` with `[ defaults ] 1 1 ...`).
- **Revision vs outline:** do NOT auto-convert Å→nm. GRO is nm by spec; rely on existing >50nm rejection.

### 40-02 — Implement sys.modules injection + cleanup (main-thread registration)
- In `custom_guest_bridge.py`:
  - `custom_guest_module(guest_type, module)` context manager (try/finally pop).
  - `register_custom_guest(...)` / `unregister_custom_guest(...)` pair for GUI async (QThread `finished` signal).
  - Assert key absent before inject; `pop(..., None)` on cleanup.
- Unit tests (TEST-02): injection makes `safe_import` return the module; cleanup removes it; re-register after cleanup works; exception during generation still cleans up (finally); residue name in generated GRO == `Molecule.name_`.

### 40-03 — Custom guest GRO/ITP validation (parseable, name length, comb-rule)
- Consolidate the validation surface (much of it built in 40-01): a single `validate_custom_guest_files(gro_path, itp_path) -> ValidationResult` returning errors/warnings with the **specific messages** required by success criteria #2/#3.
- Specific reject messages:
  - Name too long: `"Custom guest residue name '<name>' (<n> chars) exceeds 3 chars. GRO format allows 5-char residue names; QuickIce reserves 2 chars for the '_H' hydrate suffix."`
  - comb-rule=1: `"ITP comb-rule must be 2 (Lorentz-Berthelot / AMBER-GAFF2); got comb-rule=1. QuickIce does not auto-convert A/B rules. Please regenerate the ITP with comb-rule=2."`
- Add NEW test fixture `quickice/data/custom/test_invalid/etoh_combrule1.itp` containing `[ defaults ]` with comb-rule=1 to exercise the reject path.
- Extend `transform_guest_itp` (gromacs_writer.py) to **rewrite `[ atoms ]` resname** → `{residue_name}_H` for custom guests (deferred Phase 38-04 item).

### 40-04 — Integrate custom guest bridge into hydrate generator
- `HydrateConfig` (types.py): add `guest_residue_name: str = ""`; relax `__post_init__` to accept custom `guest_type` (not in `GUEST_MOLECULES`) when a custom-guest flag/path is set; auto-populate `guest_atom_labels`/`guest_atom_count` from the uploaded GRO (per [38-01], custom types must provide metadata explicitly — the bridge supplies it).
- `HydrateStructureGenerator.generate()` / `_run_via_api`: when custom guest, build+register module (main thread) → call `_run_via_api` (which already passes `guest_type` through to `parse_guest`) → cleanup in finally.
- `_build_molecule_index`: use `guest_residue_name` (fallback `guest_type.upper()`) for residue grouping.
- E2E test (TEST-05 anchor): `HydrateStructureGenerator().generate(HydrateConfig(lattice_type="sI", guest_type="etoh_custom", guest_residue_name="MOL", guest_atom_labels=[...9...], guest_atom_count=9, guest_itp_path=...))` → `HydrateStructure` with `guest_count > 0`, mol_types contains the custom type, water_count > 0. (Mirrors `tests/conftest.py` `hydrate_sI_ch4_structure` fixture pattern, module-scoped.)
- Note: GROMACS `.gro`/`.top` export with `_H` suffix + grompp validation is **Phase 41** (EXPORT-*), not Phase 40. Phase 40 only needs `generate()` to produce a correct `HydrateStructure`; the export wiring (registry in `write_multi_molecule_gro_file` line 1447 currently restricts to `["ch4","thf","co2","h2"]`) is Phase 41's scope.
