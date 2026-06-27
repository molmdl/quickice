# GenIce3 Migration Impact Assessment

**Project:** QuickIce GenIce3 Upgrade
**Domain:** Ice/hydrate structure generation library upgrade
**Mode:** Feasibility
**Assessed:** 2026-06-27
**Overall confidence:** MEDIUM-HIGH (code changes are well-understood; GenIce3 API verified from official docs; Python 3.14 blocker unresolved)

---

## 1. File-by-File Migration Impact Table

| # | File | Category | Lines Changed (est.) | Risk | Effort | GenIce2 References |
|---|------|----------|----------------------|------|--------|---------------------|
| 1 | `quickice/structure_generation/generator.py` | **Core** | 12–18 | HIGH | MEDIUM | `safe_import`, `GenIce`, `tip3p`, `depol='strict'`, `generate_ice()` |
| 2 | `quickice/structure_generation/hydrate_generator.py` | **Core** | 25–35 | HIGH | HIGH | `safe_import`, `GenIce`, `tip4p`, `depol='strict'`, `parse_guest`, `generate_ice()`, cage naming `"12"/"14"/"16"`, `genice2.*` imports |
| 3 | `quickice/structure_generation/mapper.py` | Core | 0–2 | LOW | LOW | No direct GenIce2 imports; only GenIce2 naming convention via `PHASE_TO_GENICE` dict |
| 4 | `quickice/structure_generation/gro_parser.py` | Core | 0 | NONE | NONE | No GenIce2 references; pure GRO format parser |
| 5 | `quickice/structure_generation/types.py` | Core | 6–10 | MEDIUM | LOW | `HYDRATE_LATTICES` dict (`genice_name` values `CS1`/`CS2`/`sH`), `get_genice_lattice_name()` docstring |
| 6 | `quickice/output/gromacs_writer.py` | Core | 8–15 | **CRITICAL** | HIGH | 3→4 atom normalization (`write_gro_file` assumes 3-atom input from GenIce2); `write_interface_gro_file` handles both 3/4 atom ice |
| 7 | `quickice/gui/hydrate_worker.py` | GUI | 4–6 | LOW | LOW | Docstrings/comments referencing GenIce2; no API calls |
| 8 | `quickice/gui/hydrate_panel.py` | GUI | 2–3 | LOW | LOW | Help icon text `"Uses GenIce2 for structure generation"` |
| 9 | `quickice/gui/help_dialog.py` | GUI | 1–2 | LOW | LOW | URL `"https://github.com/genice-dev/GenIce2"` |
| 10 | `quickice/gui/main_window.py` | GUI | 4–6 | LOW | LOW | Citation comments referencing GenIce2; error messages |
| 11 | `quickice/gui/vtk_utils.py` | GUI | 1–2 | LOW | LOW | Comment `"H-first methane (H, H, H, H, C) from GenIce2"` |
| 12 | `quickice/phase_mapping/data/ice_boundaries.py` | Data | 1 | NONE | NONE | Comment citing GenIce2 as data source |
| 13 | `quickice/utils/molecule_utils.py` | Utils | 1–2 | LOW | LOW | Comment `"GenIce2 output"` for H-first CH4 |
| 14 | `quickice/structure_generation/water_filler.py` | Core | 2–3 | LOW | LOW | Comments about `filter_molecules=False` for GenIce2 guests |
| 15 | `quickice/structure_generation/modes/slab.py` | Core | 1–2 | LOW | LOW | Comment about `filter_molecules=False` for GenIce2 guests |
| 16 | `quickice/structure_generation/modes/pocket.py` | Core | 1–2 | LOW | LOW | Comment about `filter_molecules=False` for GenIce2 guests |
| 17 | `environment.yml` | Infra | 2 | **CRITICAL** | LOW | `genice2==2.2.13.1`, `genice-core==1.4.3` pins |
| 18 | `quickice-gui.spec` | Infra | 1–2 | MEDIUM | LOW | `genice2`, `genice_core` in hiddenimports loop |
| 19 | `tests/conftest.py` | Tests | 3–5 | MEDIUM | MEDIUM | GenIce2 fixture construction using `IceStructureGenerator`, `HydrateStructureGenerator` |
| 20 | `tests/test_structure_generation.py` | Tests | 5–10 | MEDIUM | MEDIUM | Atom count assertions (`128 * 3 = 384` assumes 3-atom output) |
| 21 | `tests/test_output/test_gromacs_export_ice.py` | Tests | 8–12 | **HIGH** | HIGH | Tests 3→4 expansion specifically; atom name assertions |
| 22 | `tests/test_output/test_gromacs_export_interface.py` | Tests | 6–10 | MEDIUM | MEDIUM | 3→4 expansion in interface context |
| 23 | `tests/test_e2e_*.py` (8 files) | Tests | 3–6 each | LOW | LOW | Comment-only references to GenIce2; fixture-driven |
| 24 | `README.md` | Docs | 8–12 | NONE | LOW | GenIce2 references, URLs, citation section |
| 25 | `docs/cli-reference.md` | Docs | 3–5 | NONE | LOW | GenIce2 mentions |
| 26 | `docs/principles.md` | Docs | 5–8 | NONE | LOW | GenIce2 description and citation |

**Summary:** ~26 files touched; ~100–150 LOC of substantive API changes; ~50–80 LOC of comment/docstring updates.

---

## 2. Code Change Details — Specific Before/After

### 2.1 `quickice/structure_generation/generator.py` (CRITICAL — ice generation)

**Current code (GenIce2):**
```python
from genice2.plugin import safe_import
from genice2.genice import GenIce

# In _generate_single():
lattice = safe_import('lattice', self.lattice_name).Lattice()
ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)
water = safe_import('molecule', 'tip3p').Molecule()
formatter = safe_import('format', 'gromacs').Format()
gro_string = ice.generate_ice(formatter=formatter, water=water, depol='strict')
```

**Migrated code (GenIce3):**
```python
from genice3.genice import GenIce3
from genice3.plugin import Exporter, UnitCell

# In _generate_single():
unitcell = UnitCell(self.lattice_name)
genice = GenIce3(
    seed=seed,
    pol_loop_1=2000,           # equivalent to depol='strict'
    replication_matrix=self.supercell_matrix,
)
genice.set_unitcell(self.lattice_name, density=self.density)
gro_string = Exporter("gromacs").dumps(genice, water_model="ice")
```

**Key changes:**
1. **Import changes:** `genice2.plugin.safe_import` → `genice3.plugin.UnitCell` / `Exporter`
2. **Constructor change:** `GenIce(lattice, density=..., reshape=...)` → `GenIce3(replication_matrix=..., pol_loop_1=2000)` + `set_unitcell(name, density=...)`
3. **Water model:** `safe_import('molecule', 'tip3p').Molecule()` → `water_model="ice"` (exporter suboption)
4. **Depolarization:** `depol='strict'` → `pol_loop_1=2000` (constructor parameter)
5. **Output method:** `ice.generate_ice(formatter=formatter, water=water, ...)` → `Exporter("gromacs").dumps(genice, water_model="ice")`
6. **Return value:** `dumps()` returns string (same as `generate_ice()` in GenIce2, but must verify)

**⚠️ CRITICAL IMPLICATION:** With `water_model="ice"`, GenIce3 outputs **4 atoms per molecule** (OW, HW1, HW2, MW) directly. This eliminates the 3→4 atom normalization currently done in `gromacs_writer.py`. See Section 4 for the cascade effect.

**Random state save/restore:**
- GenIce2: Uses global `np.random.seed()` — QuickIce has save/restore workaround (lines 101-157)
- GenIce3: Accepts `seed` parameter in constructor — **the workaround can be REMOVED**
- However, we may still want to save/restore as a defensive measure until GenIce3's global state behavior is verified

**Confidence:** HIGH — verified from [GenIce3 API examples](https://genice-dev.github.io/GenIce3/api-examples/basic.html) and [guest occupancy examples](https://genice-dev.github.io/GenIce3/api-examples/guest_occupancy.html)

---

### 2.2 `quickice/structure_generation/hydrate_generator.py` (CRITICAL — hydrate generation)

**Current code (GenIce2):**
```python
import genice2.genice as genice_lib
from genice2.formats import gromacs
from genice2.lattices import sI, sII, sH
from genice2.molecules.tip4p import Molecule as TIP4P

# In _run_via_api():
from genice2.genice import GenIce
from genice2.plugin import safe_import
from genice2.valueparser import parse_guest

lattice = safe_import('lattice', lattice_name).Lattice()
ice = GenIce(lattice, reshape=supercell_matrix)
water = safe_import('molecule', 'tip4p').Molecule()
formatter = safe_import('format', 'gromacs').Format()

# Guest spec with numeric cage names
guests = defaultdict(dict)
guest_spec = f"12={guest_name}*{small_occ}"    # "12" for 5^12 small cage
parse_guest(guests, guest_spec)
large_cage = "14"  # sI large cage
large_cage = "16"  # sII/sH large cage
guest_spec = f"{large_cage}={guest_name}*{large_occ}"
parse_guest(guests, guest_spec)

gro_string = ice.generate_ice(formatter=formatter, water=water, guests=guests, depol='strict')
```

**Migrated code (GenIce3):**
```python
from genice3.genice import GenIce3
from genice3.plugin import Exporter, UnitCell
from genice3.cli.options import parse_guest_option

# In _run_via_api():
unitcell = UnitCell(lattice_name)
genice = GenIce3(
    seed=config.seed,  # if deterministic behavior desired
    pol_loop_1=2000,
    replication_matrix=supercell_matrix,
)
genice.set_unitcell(lattice_name)

# Guest spec with "A" prefixed cage names
guest_dict = {}
guest_spec = f"A12={guest_name}*{small_occ}"    # "A12" for 5^12 small cage
large_cage = "A14"  # sI large cage (5^12 6^2)
large_cage = "A16"  # sII large cage (5^12 6^4)
guest_spec = f"{large_cage}={guest_name}*{large_occ}"
# parse_guest_option takes a dict, not a string
guest_dict_raw = {"A12": guest_name, "A14": guest_name}  # or with occupancy
genice._guests = parse_guest_option(guest_dict_raw)  # tentative API — needs verification

gro_string = Exporter("gromacs").dumps(genice, water_model="ice")
```

**Key changes:**
1. **Cage naming:** `"12"` → `"A12"`, `"14"` → `"A14"`, `"16"` → `"A16"` (GenIce3 adds "A" prefix)
2. **Guest parsing:** `genice2.valueparser.parse_guest()` → `genice3.cli.options.parse_guest_option()` (different function signature — takes dict, not string)
3. **Water model for hydrate:** Already uses TIP4P in GenIce2; in GenIce3, use `water_model="ice"` for TIP4P/Ice
4. **Lattice loading:** `safe_import('lattice', ...)` → `UnitCell(...)` or `genice.set_unitcell(...)`
5. **Depolarization:** Same as ice: `depol='strict'` → `pol_loop_1=2000`

**⚠️ sH CAGE NAMING INVESTIGATION:**

Current code (line 200): `large_cage = "16"  # Default for sH`

In GenIce2, sH's large cage (5¹²6⁸, 28-water cage) was labeled "16". But GenIce3 uses a different naming convention where cage names correspond to the number of water molecules in the cage face. The sH large cage in GenIce3 is likely **"A20"** (20-hedron) or **"A16"** — this needs verification.

From the GenIce3 docs, the cage naming convention uses the total number of faces: 5¹²6² = 14-hedron → "A14", 5¹²6⁴ = 16-hedron → "A16". For sH's 5¹²6⁸, that would be a 20-hedron → **"A20"**. However, GenIce2 used "16" for sH's large cage, which corresponds to a 16-hedron notation (possibly using different face counting).

**ACTION REQUIRED:** Verify sH cage naming in GenIce3 by running:
```bash
genice3 sH --rep 1 1 1 -e cage_survey
```
Or via API:
```python
genice = GenIce3()
genice.set_unitcell("sH")
Exporter("cage_survey").dump(genice)
```
Look at the JSON output for cage type names.

**Confidence:** MEDIUM — cage naming for sI/sII is verified; sH needs runtime verification

---

### 2.3 `quickice/structure_generation/types.py` (LOW — type definitions)

**Changes needed:**
```python
# Current:
HYDRATE_LATTICES = {
    "sI":  {"genice_name": "CS1", ...},  # GenIce2 lattice name
    "sII": {"genice_name": "CS2", ...},  # GenIce2 lattice name
    "sH":  {"genice_name": "sH", ...},   # GenIce2 lattice name
}

# After migration (if lattice names change in GenIce3):
HYDRATE_LATTICES = {
    "sI":  {"genice_name": "CS1", ...},  # Same in GenIce3? Needs verification
    "sII": {"genice_name": "CS2", ...},  # Same in GenIce3? Needs verification
    "sH":  {"genice_name": "sH", ...},   # Same in GenIce3? Needs verification
}
```

**Note:** GenIce3 unit cell names may differ from GenIce2 lattice names. The GenIce3 docs show:
- sI hydrate → `"CS1"` or `"1"` (needs verification)
- sII hydrate → `"CS2"` or `"2"` (needs verification)
- sH hydrate → `"sH"` or `"H"` (needs verification)

From the GenIce3 unit cells page, hydrate names are: `CS1`, `CS2`, `sH` — these appear to be unchanged.

**Also update docstrings:**
- Line 83: `"GenIce2 lattice names"` → `"GenIce3 lattice names"`
- Line 391: `"Get GenIce2 lattice name"` → `"Get GenIce3 lattice name"`

**Confidence:** MEDIUM — lattice names likely unchanged but need verification

---

### 2.4 `quickice/structure_generation/mapper.py` (LOW — phase name mapping)

**Current:**
```python
PHASE_TO_GENICE = {
    "ice_ih": "ice1h",
    "ice_ic": "ice1c",
    "ice_ii": "ice2",
    "ice_iii": "ice3",
    "ice_v": "ice5",
    "ice_vi": "ice6",
    "ice_vii": "ice7",
    "ice_viii": "ice8",
}
```

**GenIce3 naming convention:** GenIce3 uses numeric names without the "ice" prefix:
- `"1h"` or `"Ih"` for Ice Ih (was `"ice1h"` in GenIce2)
- `"1c"` or `"Ic"` for Ice Ic (was `"ice1c"` in GenIce2)
- `"2"` for Ice II (was `"ice2"` in GenIce2)
- etc.

From GenIce3 unit cells documentation:
| GenIce2 | GenIce3 | Notes |
|---------|---------|-------|
| `ice1h` | `1h` | Hexagonal ice |
| `ice1c` | `1c` | Cubic ice |
| `ice2` | `2` | Ice II |
| `ice3` | `3` | Ice III |
| `ice5` | `5` | Ice V |
| `ice6` | `6` | Ice VI |
| `ice7` | `7` | Ice VII |
| `ice8` | `8` | Ice VIII |

**Migrated:**
```python
PHASE_TO_GENICE = {
    "ice_ih": "1h",
    "ice_ic": "1c",
    "ice_ii": "2",
    "ice_iii": "3",
    "ice_v": "5",
    "ice_vi": "6",
    "ice_vii": "7",
    "ice_viii": "8",
}
```

Also update `UNIT_CELL_MOLECULES` dict keys accordingly.

**Confidence:** HIGH — verified from [GenIce3 unit cells page](https://genice-dev.github.io/GenIce3/unitcells.html)

---

### 2.5 `quickice/structure_generation/gro_parser.py` (NO CHANGE)

The GRO parser is a pure format parser with zero GenIce2 references. GenIce3's GROMACS exporter produces the same GRO format (fixed-width columns, same residue names, same atom names). **No changes needed.**

**Confidence:** HIGH — GRO format is a GROMACS standard, not GenIce-specific

---

### 2.6 `quickice/output/gromacs_writer.py` (CRITICAL — 3→4 atom normalization)

This is the **most complex and highest-risk** change in the migration.

**Current behavior (GenIce2 era):**
- `generator.py` produces ice candidates with **3 atoms/molecule** (O, H, H from TIP3P)
- `gromacs_writer.py:write_gro_file()` expands each molecule from 3→4 atoms at export time by:
  1. Using `mol_idx * 3` as the base index (line 680)
  2. Computing `MW = O + α*(H1-O) + α*(H2-O)` (line 686)
  3. Writing 4 GRO lines per molecule: OW, HW1, HW2, MW (lines 692-712)
- `write_interface_gro_file()` handles BOTH cases:
  - Classic ice (3 atoms): computes MW (lines 929-933)
  - Hydrate ice (4 atoms): uses existing MW (lines 934-939)

**After GenIce3 migration with `water_model="ice"`:**
- `generator.py` would produce candidates with **4 atoms/molecule** (OW, HW1, HW2, MW)
- `write_gro_file()` **MUST be rewritten** because:
  - It currently assumes `mol_idx * 3` indexing (3 atoms per molecule)
  - It computes MW from O, H1, H2 — but MW already exists in the 4-atom output
  - Total atom count would be `nmol * 4` in the input (not `nmol * 3`)

**Two migration strategies:**

#### Strategy A: Adapt `gromacs_writer.py` to handle 4-atom input (RECOMMENDED)

```python
def write_gro_file(candidate: Candidate, filepath: str) -> None:
    nmol = candidate.nmolecules
    # Detect atoms per molecule from candidate
    atoms_per_mol = detect_atoms_per_molecule(candidate.atom_names)
    n_atoms = nmol * 4  # Output is always 4-atom TIP4P-ICE

    ice_molecule_index = [
        MoleculeIndex(start_idx=i * atoms_per_mol, count=atoms_per_mol, mol_type="ice")
        for i in range(nmol)
    ]
    wrapped_positions = wrap_molecules_into_box(candidate.positions, ice_molecule_index, candidate.cell)

    for mol_idx in range(nmol):
        base_idx = mol_idx * atoms_per_mol
        if atoms_per_mol == 3:
            # Legacy 3-atom input — compute MW
            o_pos = wrapped_positions[base_idx]
            h1_pos = wrapped_positions[base_idx + 1]
            h2_pos = wrapped_positions[base_idx + 2]
            mw_pos = compute_mw_position(o_pos, h1_pos, h2_pos)
        else:
            # 4-atom input — MW already present
            o_pos = wrapped_positions[base_idx]
            h1_pos = wrapped_positions[base_idx + 1]
            h2_pos = wrapped_positions[base_idx + 2]
            mw_pos = wrapped_positions[base_idx + 3]
        # ... write OW, HW1, HW2, MW lines (same as now)
```

**Pros:** Backward-compatible (handles both 3-atom and 4-atom input); minimal disruption to downstream code.
**Cons:** Slightly more complex code; `detect_atoms_per_molecule` already exists.

#### Strategy B: Remove normalization entirely (if GenIce3 is mandatory)

If we require GenIce3 and drop GenIce2 support, we can simplify:
- Remove all 3→4 expansion logic
- Assume all input candidates have 4 atoms per molecule
- Remove `compute_mw_position()` from ice export path (keep for interface path until hydrate also migrates)

**Pros:** Simpler code; removes a significant source of bugs.
**Cons:** Breaking change if any test/data uses 3-atom format.

**Recommendation:** Strategy A during transition (support both); Strategy B after GenIce2 is fully dropped.

**Confidence:** HIGH — the change is mechanical and well-understood

---

### 2.7 `environment.yml` (CRITICAL — dependency pinning)

**Current:**
```yaml
- pip:
    - genice-core==1.4.3
    - genice2==2.2.13.1
```

**After migration:**
```yaml
- pip:
    - genice-core>=1.5.4    # Required by GenIce3; API breaking change from 1.4.3
    - genice3>=3.0b4        # Replace genice2
```

**⚠️ BLOCKER:** GenIce3's `pyproject.toml` specifies `Python <3.14, >=3.11`. QuickIce uses Python 3.14.3.

**Resolution options:**
1. **Request Python 3.14 support from GenIce3 maintainer** (likely — the constraint may be conservative)
2. **One-line patch:** Edit GenIce3's `pyproject.toml` after install to remove the upper bound
3. **Downgrade QuickIce to Python 3.13** (not recommended — would break our environment)
4. **Wait for GenIce3 stable release** with updated Python support

**Additional deps from GenIce3:** pyyaml, jinja2 (these may already be in our env or are small enough to add)

**Confidence:** HIGH for the change pattern; LOW for the Python 3.14 resolution timeline

---

### 2.8 `quickice-gui.spec` (PyInstaller — MEDIUM)

**Current (line 9):**
```python
for pkg in ['iapws', 'genice2', 'genice_core', 'matplotlib', ...]:
```

**After migration:**
```python
for pkg in ['iapws', 'genice3', 'genice_core', 'matplotlib', ...]:
```

Note: `genice_core` package name stays the same (it's a separate package). Only the GenIce2→3 package name changes.

**Risk:** PyInstaller may not correctly bundle GenIce3's plugin system (which uses `safe_import` / entry points differently). This requires testing after migration.

**Confidence:** MEDIUM — simple text change, but PyInstaller plugin discovery needs runtime verification

---

### 2.9 GUI Files (LOW — text/comment updates)

| File | Change |
|------|--------|
| `hydrate_worker.py` | Update docstrings: `"GenIce2"` → `"GenIce3"` in 4 places (lines 1, 3, 18, 90, 99) |
| `hydrate_panel.py` | Help icon text: `"Uses GenIce2"` → `"Uses GenIce3"` (line 95) |
| `help_dialog.py` | URL: `"https://github.com/genice-dev/GenIce2"` → `"https://github.com/genice-dev/GenIce3"` (line 212) |
| `main_window.py` | Citation comments (lines 2034, 2042, 2043, 2055, 2057) — update URLs and text |
| `vtk_utils.py` | Comment on line 726 — change `"from GenIce2"` → `"from GenIce3"` |

All are cosmetic — no API or logic changes.

---

## 3. Test Migration Plan

### 3.1 Test Files Requiring Changes

| Test File | Change Type | Effort | Notes |
|-----------|-------------|--------|-------|
| `tests/conftest.py` | **API change** | MEDIUM | Fixtures construct `IceStructureGenerator` / `HydrateStructureGenerator` — these internally use GenIce2 API; no change needed if generator API is stable (it should be) |
| `tests/test_structure_generation.py` | **Assertion change** | MEDIUM | Line 343: `128 * 3 = 384` assumes 3-atom output; with GenIce3 + `water_model="ice"`, would be `128 * 4 = 512` |
| `tests/test_output/test_gromacs_export_ice.py` | **Major rewrite** | HIGH | Tests 3→4 expansion specifically; expects 3-atom input; must handle 4-atom input from GenIce3 |
| `tests/test_output/test_gromacs_export_interface.py` | **Update** | MEDIUM | Tests interface 3→4 expansion; same issue as above |
| `tests/test_atom_ordering_validation.py` | **Minor** | LOW | Tests for `["OW", "HW1", "HW2", "MW"]` pattern — still valid with GenIce3 |
| `tests/test_interface_ordering_validation.py` | **Minor** | LOW | Already handles both 3-atom and 4-atom ice patterns |
| `tests/test_e2e_*.py` (8 files) | **Comments only** | LOW | References to GenIce2 in docstrings/comments; fixtures still work if generators work |
| `tests/test_scancode_bugs_gromacs.py` | **MW position test** | MEDIUM | Tests MW computation from O, H1, H2; may need updating if MW comes from GenIce3 directly |

### 3.2 Atom Count Impact

**Current assumption across codebase:** Ice candidates from GenIce2 have 3 atoms/molecule.

After GenIce3 migration with `water_model="ice"`, candidates have 4 atoms/molecule. This changes:

| Metric | GenIce2 (current) | GenIce3 (migrated) |
|--------|-------------------|-------------------|
| Ice candidate atoms | `nmol * 3` | `nmol * 4` |
| GRO output atoms | `nmol * 4` (MW added at export) | `nmol * 4` (MW already present) |
| `Candidate.atom_names` | `["O", "H", "H", ...]` | `["OW", "HW1", "HW2", "MW", ...]` |
| `Candidate.positions` shape | `(nmol*3, 3)` | `(nmol*4, 3)` |

**Every test that asserts on `len(candidate.positions)` or `len(candidate.atom_names)` must be updated.**

### 3.3 New Tests to Add

1. **GenIce3 API smoke test:** Verify `GenIce3`, `Exporter`, `UnitCell` imports work
2. **4-atom candidate round-trip test:** Generate with GenIce3, export to GRO, verify atom names
3. **Cage naming verification test:** Generate sI/sII/sH hydrate, verify cage guest placement
4. **sH cage naming test:** Verify the A-prefix for sH's large cage

---

## 4. TIP4P/Ice `water_model="ice"` — Does It Eliminate Normalization?

**Current normalization flow:**

```
GenIce2 (tip3p) → Candidate{positions: (N*3, 3), atom_names: ["O","H","H",...]}
                                    ↓
gromacs_writer.py (write_gro_file):
  - Read 3 atoms per molecule
  - Compute MW = O + α*(H1-O) + α*(H2-O)
  - Write 4 GRO lines: OW, HW1, HW2, MW
                                    ↓
Output GRO file (4 atoms per molecule)
```

**After GenIce3 with `water_model="ice"`:**

```
GenIce3 (water_model="ice") → Candidate{positions: (N*4, 3), atom_names: ["OW","HW1","HW2","MW",...]}
                                    ↓
gromacs_writer.py (write_gro_file):
  - Read 4 atoms per molecule
  - MW already present — no computation needed
  - Write 4 GRO lines: OW, HW1, HW2, MW (pass-through)
                                    ↓
Output GRO file (4 atoms per molecule)
```

**Impact on `compute_mw_position()`:**

- **Ice export path (`write_gro_file`):** No longer needed if GenIce3 provides MW. But keep for backward compatibility during transition.
- **Interface export path (`write_interface_gro_file`):** Currently handles both 3-atom (classic ice) and 4-atom (hydrate) ice. With GenIce3, ALL ice would be 4-atom. The 3-atom code path would only be needed for backward compatibility or if we keep GenIce2 support.
- **`detect_atoms_per_molecule()`:** Already exists in `types.py` — returns 3 or 4 based on first atom name. Can be reused.

**Recommendation:**
1. During transition: Keep both paths in `gromacs_writer.py` (detect 3 vs 4 atoms per molecule)
2. After GenIce2 is dropped: Remove the 3-atom code path and `compute_mw_position()` from ice-only export
3. Keep `compute_mw_position()` available for any future 3-atom input scenarios

**Confidence:** HIGH — this is a mechanical change; the normalization logic is well-understood

---

## 5. Adapter Layer Feasibility Assessment

### Can we support BOTH GenIce2 and GenIce3 with runtime detection?

**Answer: NO — not in the same environment.** (Confidence: HIGH)

**Reason:** GenIce2 requires `genice-core==1.4.3` and GenIce3 requires `genice-core>=1.5.4`. These versions are **mutually exclusive** because `genice-core` 1.5.4+ has breaking API changes (e.g., `ice_graph` signature changed). They cannot coexist in the same Python environment.

### Adapter Pattern Options

#### Option 1: Environment-level switching (separate conda envs)
- Maintain two environments: `quickice` (GenIce2) and `quickice-genice3` (GenIce3)
- Code detects which GenIce version is available at import time
- **Pros:** Clean separation; no API conflicts
- **Cons:** Doubles testing matrix; users must manage two envs

#### Option 2: Import-level adapter
```python
# quickice/structure_generation/genice_adapter.py
try:
    from genice3.genice import GenIce3
    GENICE_VERSION = 3
except ImportError:
    from genice2.genice import GenIce
    GENICE_VERSION = 2

class IceGeneratorAdapter:
    """Unified interface for ice generation across GenIce versions."""
    def generate(self, lattice_name, density, supercell_matrix, seed, depol_mode):
        if GENICE_VERSION == 3:
            return self._generate_v3(...)
        else:
            return self._generate_v2(...)
```

**Pros:** Single codebase supports both; clean abstraction
**Cons:** Cannot install both packages simultaneously; adapter code is dead weight once migration is complete; `genice-core` version conflict prevents actual dual support

#### Option 3: Full migration (RECOMMENDED)
- Create a migration branch
- Replace all GenIce2 code with GenIce3
- Update all tests
- Verify with full test suite
- Merge when stable

**Pros:** Clean; no adapter overhead; gets all GenIce3 benefits
**Cons:** Cannot roll back without reverting the branch

### Recommendation

**Full migration (Option 3)** is the only practical approach because:
1. GenIce2 and GenIce3 cannot coexist in the same environment (`genice-core` conflict)
2. An adapter layer would be dead code once migration is complete
3. The blast radius is manageable (~100-150 LOC of API changes)

**Migration strategy:**
1. Create `feature/genice3-migration` branch
2. Update `environment.yml` with GenIce3 deps
3. Resolve Python 3.14 upper bound (one-line patch or maintainer request)
4. Migrate `generator.py` and `hydrate_generator.py`
5. Update `gromacs_writer.py` to handle 4-atom candidates
6. Update tests
7. Update GUI text/URLs
8. Run full test suite
9. Merge when all tests pass

**Confidence:** HIGH

---

## 6. sH Hydrate Cage Naming Investigation

### Current Code (GenIce2)

```python
# hydrate_generator.py line 186-200
if small_occ > 0:
    guest_spec = f"12={guest_name}"        # "12" = 5^12 cage
if large_occ > 0:
    if config.lattice_type == "sI":
        large_cage = "14"                  # 5^12 6^2 = 14-hedron
    elif config.lattice_type == "sII":
        large_cage = "16"                  # 5^12 6^4 = 16-hedron
    else:
        large_cage = "16"                  # Default for sH ← POSSIBLE BUG
```

### GenIce3 Cage Naming Convention

GenIce3 prefixes all cage names with "A":
- 5¹² (small) → `"A12"`
- 5¹²6² (sI large) → `"A14"`
- 5¹²6⁴ (sII large) → `"A16"`

For sH, the cage types are:
- Small: 5¹² → `"A12"`
- Medium: 4³5⁶6³ → This is a **15-hedron** → `"A15"` or maybe `"A36"` depending on counting convention
- Large: 5¹²6⁸ → This is a **20-hedron** → `"A20"` (most likely)

### The Problem

Current code assigns `"16"` for sH's large cage, which in GenIce2 maps to the 5¹²6⁴ cage (16-hedron). But sH's large cage is 5¹²6⁸ (20-hedron), which would be `"A20"` in GenIce3.

**GenIce2 may have had a bug here** — sH's large cage is NOT the same as sII's large cage (5¹²6⁴). Using `"16"` for sH may have worked because GenIce2's `parse_guest` mapped cage numbers differently, but it's semantically incorrect.

### Verification Plan

1. Run `genice3 sH --rep 1 1 1 -e cage_survey` and inspect JSON output
2. Look for cage type names in the output
3. Map each cage name to the correct QuickIce cage category (small/medium/large)
4. Update `hydrate_generator.py` accordingly

### Also Check: sH Medium Cage

GenIce3's sH may expose the medium cage (4³5⁶6³) separately. Currently, QuickIce only supports **small** and **large** cage occupancy for sH. The medium cage would be a new concept for QuickIce's UI.

**Action items:**
1. Verify sH cage names in GenIce3
2. Decide whether to expose sH medium cage occupancy in QuickIce UI
3. Update `hydrate_generator.py` cage name mapping

**Confidence:** LOW — needs runtime verification

---

## 7. Risk Register

| # | Risk | Severity | Likelihood | Mitigation |
|---|------|----------|------------|------------|
| R1 | **Python 3.14 upper bound in GenIce3 prevents installation** | CRITICAL | HIGH | Request maintainer to lift bound; one-line patch in `pyproject.toml`; or downgrade Python |
| R2 | **3→4 atom normalization removal causes GRO export regressions** | HIGH | MEDIUM | Keep backward-compatible 3-atom path during transition; add comprehensive tests |
| R3 | **GenIce3 is beta (3.0b3/3.0b4) — API may change before stable** | HIGH | MEDIUM | Pin to specific beta version; track changelog; wait for stable if risk-averse |
| R4 | **sH cage naming wrong in GenIce3** | MEDIUM | MEDIUM | Verify with cage_survey before updating; add sH-specific integration test |
| R5 | **GenIce3 `dumps()` returns different GRO format than `generate_ice()`** | MEDIUM | LOW | Write round-trip test: generate → parse with `gro_parser.py` → verify structure |
| R6 | **`parse_guest_option()` API differs from `parse_guest()`** | MEDIUM | MEDIUM | Read GenIce3 source for `parse_guest_option`; test with known hydrate configs |
| R7 | **PyInstaller fails to bundle GenIce3 plugins** | MEDIUM | MEDIUM | Test PyInstaller build after migration; add `genice3` to `hiddenimports` loop |
| R8 | **GenIce3 still uses global `np.random.seed()` internally** | LOW | LOW | Keep save/restore pattern until verified; GenIce3's `seed` parameter should handle this |
| R9 | **fastapi/uvicorn deps pulled in by GenIce3** (packaging bug) | LOW | HIGH | Accept as transient dep; or exclude in PyInstaller spec |
| R10 | **GenIce3 hydrate guest molecule naming differs** | MEDIUM | MEDIUM | Verify CH4/THF residue names in GenIce3 output match our `_build_molecule_index()` expectations |
| R11 | **Interface builder assumes 3-atom ice from generator** | HIGH | MEDIUM | Update `slab.py`, `pocket.py`, `piece.py` to handle 4-atom ice candidates |
| R12 | **`genice-core` 1.5.4+ API changes break other parts of codebase** | MEDIUM | LOW | We don't import `genice_core` directly — all access is through GenIce2/3 |

---

## 8. Effort Estimate

### LOC Changes by Category

| Category | Files | Substantive LOC | Comment/Doc LOC | Risk |
|----------|-------|-----------------|-----------------|------|
| Core API migration | 3 (generator, hydrate_gen, types) | 50–70 | 10–15 | HIGH |
| GROMACS writer adaptation | 1 (gromacs_writer) | 30–50 | 10–15 | CRITICAL |
| Mapper updates | 1 (mapper.py) | 8–10 | 5 | LOW |
| GUI text/URL updates | 5 files | 0 | 20–30 | NONE |
| Environment/infra | 2 (environment.yml, spec) | 2 | 0 | CRITICAL |
| Test updates | 12 files | 40–70 | 20–30 | MEDIUM |
| Documentation | 3 (README, cli-ref, principles) | 0 | 20–30 | NONE |
| Utility comments | 4 (molecule_utils, water_filler, slab, pocket) | 0 | 8–12 | NONE |
| **Total** | **~26 files** | **130–200** | **93–132** | |

### Approximate Execution Time

| Phase | Duration | Dependencies |
|-------|----------|-------------|
| 1. Environment setup (Python 3.14 fix, GenIce3 install) | 0.5–1 day | R1 must be resolved |
| 2. Core API migration (generator.py, hydrate_generator.py) | 1–2 days | Phase 1 complete |
| 3. GROMACS writer adaptation | 1–2 days | Phase 2 complete (need 4-atom candidates) |
| 4. Interface builder updates | 0.5–1 day | Phase 2 complete |
| 5. Test migration | 1–2 days | Phases 2–4 complete |
| 6. GUI/infra/docs updates | 0.5 day | Phases 2–3 complete |
| 7. Integration testing + bug fixes | 1–2 days | Phases 2–6 complete |
| 8. PyInstaller verification | 0.5–1 day | Phase 7 complete |
| **Total** | **6–11 days** | |

### Execution Complexity

- **Simple (mechanical):** mapper.py, types.py, GUI text, docs, environment.yml — ~2 days
- **Moderate (requires understanding):** generator.py, hydrate_generator.py — ~3 days
- **Complex (requires design decisions):** gromacs_writer.py, interface builders — ~3 days
- **Validation (requires runtime testing):** Tests, PyInstaller, sH cage names — ~3 days

---

## 9. Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Core API migration (ice) | HIGH | GenIce3 API verified from official docs; changes are mechanical |
| Core API migration (hydrate) | MEDIUM | `parse_guest_option()` API needs source-level verification; sH cage naming unknown |
| GRO format compatibility | HIGH | GRO is a GROMACS standard; GenIce3 GROMACS exporter produces same format |
| `water_model="ice"` eliminating normalization | HIGH | GenIce3 docs confirm 4-atom output; code change is straightforward |
| gromacs_writer.py adaptation | HIGH | Pattern already exists for 4-atom ice (hydrate path); just needs generalization |
| sH cage naming | LOW | No runtime verification done; requires GenIce3 installation |
| Python 3.14 compatibility | LOW | Upper bound exists in GenIce3; resolution unknown |
| PyInstaller bundling | MEDIUM | Simple text change but plugin system may differ; needs runtime test |
| Test migration | MEDIUM | Atom count changes are predictable; but edge cases may emerge |
| Adapter layer feasibility | HIGH | Confirmed impossible due to genice-core version conflict |
| Blast radius for dual support | HIGH | Confirmed that dual support is not feasible in same env |

---

## 10. Summary of Key Decisions Required

1. **Python 3.14 vs GenIce3:** Request maintainer support, or patch `pyproject.toml`, or wait?
2. **Migration timing:** Wait for GenIce3 stable release, or migrate on beta?
3. **3→4 normalization removal:** Immediate removal, or keep backward-compatible path?
4. **sH medium cage exposure:** Add UI support for sH medium cage occupancy, or keep current 2-cage model?
5. **`compute_mw_position()` fate:** Keep as utility function, or remove entirely when normalization is gone?
6. **Random state handling:** Remove save/restore workaround immediately, or keep defensively?

---

## Appendix A: GenIce3 API Quick Reference for QuickIce Migration

### GenIce3 Constructor
```python
from genice3.genice import GenIce3

genice = GenIce3(
    seed=42,                    # Random seed (replaces global np.random.seed)
    pol_loop_1=2000,            # Depolarization (replaces depol='strict')
    pol_loop_2=10000,           # Secondary polarization loop
    replication_matrix=np.array([[2,0,0],[0,2,0],[0,0,2]]),  # Supercell
    target_pol=np.array([0,0,0]),  # Target polarization vector
    guests={...},               # Guest molecules per cage type
    spot_guests={...},          # Spot guest placement
)
```

### Unit Cell Setting
```python
genice.set_unitcell("1h")      # Ice Ih
genice.set_unitcell("CS1")     # sI hydrate
genice.set_unitcell("sH")      # sH hydrate
genice.set_unitcell("1h", density=0.9)  # With density override
```

### Export
```python
from genice3.plugin import Exporter

# GROMACS format
Exporter("gromacs").dumps(genice, water_model="ice")  # Returns string
Exporter("gromacs").dump(genice, file, water_model="ice")  # Writes to file

# Water models: "3site", "4site", "ice" (TIP4P/Ice)
```

### Guest Molecules
```python
from genice3.cli.options import parse_guest_option, parse_spot_guest_option

guests = parse_guest_option({"A12": "ch4", "A14": "thf"})
genice = GenIce3(guests=guests, ...)
```

### Plugin Loading (replaces safe_import)
```python
from genice3.plugin import UnitCell, Exporter, Molecule

unitcell = UnitCell("1h")          # Load unit cell plugin
exporter = Exporter("gromacs")     # Load exporter plugin
molecule = Molecule("ch4")         # Load molecule plugin
```

---

## Appendix B: Lattice Name Mapping (GenIce2 → GenIce3)

| QuickIce phase_id | GenIce2 Name | GenIce3 Name | Unit Cell Molecules |
|-------------------|-------------|-------------|-------------------|
| `ice_ih` | `ice1h` | `1h` | 16 |
| `ice_ic` | `ice1c` | `1c` | 8 |
| `ice_ii` | `ice2` | `2` | 12 |
| `ice_iii` | `ice3` | `3` | 12 |
| `ice_v` | `ice5` | `5` | 28 |
| `ice_vi` | `ice6` | `6` | 10 |
| `ice_vii` | `ice7` | `7` | 16 |
| `ice_viii` | `ice8` | `8` | 64 |

### Hydrate Lattice Names

| QuickIce Type | GenIce2 Name | GenIce3 Name | Notes |
|--------------|-------------|-------------|-------|
| sI | `CS1` | `CS1` | Likely unchanged — needs verification |
| sII | `CS2` | `CS2` | Likely unchanged — needs verification |
| sH | `sH` | `sH` | Likely unchanged — needs verification |

### Hydrate Cage Names

| Cage Type | GenIce2 | GenIce3 | Notes |
|-----------|---------|---------|-------|
| 5¹² (small) | `"12"` | `"A12"` | A-prefix added |
| 5¹²6² (sI large) | `"14"` | `"A14"` | A-prefix added |
| 5¹²6⁴ (sII large) | `"16"` | `"A16"` | A-prefix added |
| 4³5⁶6³ (sH medium) | N/A | `"A15"`? | **NEEDS VERIFICATION** |
| 5¹²6⁸ (sH large) | `"16"` (WRONG) | `"A20"`? | **NEEDS VERIFICATION** — GenIce2 may have had a bug |

---

*End of migration impact assessment.*
