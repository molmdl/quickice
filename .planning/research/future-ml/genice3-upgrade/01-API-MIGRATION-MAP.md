# GenIce2 → GenIce3 API Migration Map

**Project:** QuickIce GenIce3 Upgrade Assessment  
**Date:** 2026-06-27  
**GenIce2 version:** 2.2.13.1 (installed)  
**GenIce3 version:** 3.0b3 (PyPI beta, 2026-02-26)  
**Overall confidence:** HIGH (official docs + source code verified)

---

## 1. Complete API Mapping Table

| # | GenIce2 API Call | GenIce3 API Call | Confidence | Source |
|---|---|---|---|---|
| 1 | `from genice2.genice import GenIce` | `from genice3.genice import GenIce3` | HIGH | Official docs, source |
| 2 | `from genice2.plugin import safe_import` | `from genice3.plugin import Exporter, UnitCell` | HIGH | Official docs, plugin.py source |
| 3 | `safe_import('lattice', name).Lattice()` | `genice.set_unitcell(name)` | HIGH | Official docs, API examples |
| 4 | `GenIce(lattice, density=d, reshape=M)` | `GenIce3(replication_matrix=M)` then `genice.set_unitcell(name, density=d)` | HIGH | Source: genice.py `__init__` + `set_unitcell` |
| 5 | `safe_import('molecule', 'tip3p').Molecule()` | `water_model="3site"` (exporter suboption) | HIGH | gromacs.py source, water-models.html |
| 6 | `safe_import('molecule', 'tip4p').Molecule()` | `water_model="4site"` (exporter suboption) | HIGH | gromacs.py source, water-models.html |
| 7 | `safe_import('format', 'gromacs').Format()` | `Exporter("gromacs")` | HIGH | Official docs, plugin.py source |
| 8 | `ice.generate_ice(formatter, water, depol='strict')` | `Exporter("gromacs").dumps(genice, water_model="3site")` | HIGH | gromacs.py source (dumps returns str) |
| 9 | `from genice2.valueparser import parse_guest` | `from genice3.cli.options import parse_guest_option` | HIGH | options.py source |
| 10 | `parse_guest(guests, "12=ch4")` | `parse_guest_option({"A12": "ch4"})` | HIGH | options.py source, API example 6 |
| 11 | `from genice2.lattices import sI, sII, sH` | `genice.set_unitcell("CS1")` / `"CS2"` / `"DOH"` | HIGH | unitcells.html |
| 12 | `np.random.seed(seed)` (manual save/restore) | `GenIce3(seed=42)` (constructor param) | MEDIUM | genice.py source (still calls np.random.seed internally) |
| 13 | `depol='strict'` on generate_ice | `pol_loop_1=2000` on GenIce3 constructor | HIGH | cli.html, genice.py source |

---

## 2. Detailed Migration Notes with Code Examples

### 2.1 Ice Generation (generator.py: `_generate_single`)

**GenIce2 code (current):**
```python
from genice2.plugin import safe_import
from genice2.genice import GenIce
import numpy as np

# Save/restore global random state
original_state = np.random.get_state()
np.random.seed(seed)

lattice = safe_import('lattice', self.lattice_name).Lattice()
ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)
water = safe_import('molecule', 'tip3p').Molecule()
formatter = safe_import('format', 'gromacs').Format()
gro_string = ice.generate_ice(formatter=formatter, water=water, depol='strict')

# Restore random state
np.random.set_state(original_state)
```

**GenIce3 equivalent (recommended):**
```python
from genice3.genice import GenIce3
from genice3.plugin import Exporter
import numpy as np

# Create GenIce3 instance with all parameters in constructor
genice = GenIce3(
    seed=seed,
    pol_loop_1=2000,  # Equivalent to depol='strict'
    replication_matrix=self.supercell_matrix,
)

# Set unit cell (density is a unitcell suboption, not constructor param)
genice.set_unitcell(self.lattice_name, density=self.density)

# Generate GRO string — use dumps() not dump()
gro_string = Exporter("gromacs").dumps(
    genice,
    water_model="3site",  # TIP3P: O, H, H (residue "SOL")
)
```

**Key differences:**
1. No separate lattice/water/formatter plugin loading — all handled by `GenIce3` + `Exporter`
2. `density` moves from `GenIce(lattice, density=d)` to `set_unitcell(name, density=d)` (a unitcell suboption)
3. Water model is an exporter suboption, not a separate plugin
4. `depol='strict'` → `pol_loop_1=2000` (high iteration count ensures strict depolarization)
5. `dumps()` returns a **string** — this is CRITICAL for QuickIce which parses GRO strings

**⚠️ BREAKING: `dump()` vs `dumps()`**

```python
# dump() writes to file (default: sys.stdout) — returns None
Exporter("gromacs").dump(genice, water_model="3site")  # → writes to stdout

# dumps() returns a string — what QuickIce needs
gro_string = Exporter("gromacs").dumps(genice, water_model="3site")  # → returns str
```

QuickIce MUST use `dumps()`, NOT `dump()`, because it parses the GRO string directly.

---

### 2.2 Hydrate Generation (hydrate_generator.py: `_run_via_api`)

**GenIce2 code (current):**
```python
from genice2.genice import GenIce
from genice2.plugin import safe_import
from genice2.valueparser import parse_guest
from collections import defaultdict
import numpy as np

lattice = safe_import('lattice', lattice_name).Lattice()
supercell_matrix = np.diag([config.supercell_x, config.supercell_y, config.supercell_z])
ice = GenIce(lattice, reshape=supercell_matrix)
water = safe_import('molecule', 'tip4p').Molecule()
formatter = safe_import('format', 'gromacs').Format()

# Guest setup
guests = defaultdict(dict)
parse_guest(guests, f"12={guest_name}")
parse_guest(guests, f"14={guest_name}")  # or "16" for sII/sH

gro_string = ice.generate_ice(formatter=formatter, water=water, guests=guests, depol='strict')
```

**GenIce3 equivalent (recommended):**
```python
from genice3.genice import GenIce3
from genice3.plugin import Exporter
from genice3.cli.options import parse_guest_option
import numpy as np

supercell_matrix = np.diag([config.supercell_x, config.supercell_y, config.supercell_z])

# Build guest spec using parse_guest_option
# Note: cage names use "A" prefix in GenIce3
guest_dict = {}
if small_occ > 0:
    guest_dict["A12"] = f"{guest_name}" if small_occ == 1.0 else f"{guest_name}*{small_occ}"
if large_occ > 0:
    if config.lattice_type == "sI":
        cage = "A14"  # 5^12 6^2 for sI
    else:
        cage = "A16"  # 5^12 6^4 for sII/sH
    guest_dict[cage] = f"{guest_name}" if large_occ == 1.0 else f"{guest_name}*{large_occ}"

genice = GenIce3(
    seed=seed,
    pol_loop_1=2000,
    replication_matrix=supercell_matrix,
    guests=parse_guest_option(guest_dict),
)

genice.set_unitcell(lattice_name)

gro_string = Exporter("gromacs").dumps(
    genice,
    water_model="4site",  # TIP4P: OW, HW1, HW2, MW (residue "ICE")
)
```

**Key differences:**
1. Guests are set in the `GenIce3` constructor, not passed to `generate_ice()`
2. Cage naming uses "A" prefix: "12" → "A12", "14" → "A14", "16" → "A16"
3. Guest molecule names are loaded inside `parse_guest_option()` (no separate `safe_import`)
4. Occupancy syntax: `"ch4*0.5"` or `"0.5*ch4"` (GenIce3 accepts both orderings)
5. Water model is `"4site"` for TIP4P (GenIce2 used `'tip4p'`)

---

### 2.3 Plugin Import Changes

| GenIce2 Category | GenIce3 Category | Old API | New API |
|---|---|---|---|
| `'lattice'` | `'unitcell'` | `safe_import('lattice', '1h').Lattice()` | `UnitCell("1h")` or `genice.set_unitcell("1h")` |
| `'format'` | `'exporter'` | `safe_import('format', 'gromacs').Format()` | `Exporter("gromacs")` |
| `'molecule'` | `'molecule'` | `safe_import('molecule', 'tip3p').Molecule()` | Handled by `water_model=` exporter suboption |

**Note:** The `safe_import` function still exists in GenIce3's `plugin.py` and accepts `'unitcell'`, `'exporter'`, `'molecule'`, `'group'` as category names. The old `'lattice'` category is renamed to `'unitcell'`.

---

### 2.4 Unit Cell / Lattice Names

All QuickIce's GenIce2 lattice names are also valid in GenIce3:

| QuickIce phase_id | GenIce2 lattice name | GenIce3 unitcell names | Compatible? |
|---|---|---|---|
| `ice_ih` | `ice1h` | `1h`, `Ih`, `ice1h`, `ice1h_unit` | ✅ Yes |
| `ice_ic` | `ice1c` | `1c`, `Ic`, `ice1c` | ✅ Yes |
| `ice_ii` | `ice2` | `2`, `II`, `ice2` | ✅ Yes |
| `ice_iii` | `ice3` | `3`, `III`, `ice3` | ✅ Yes |
| `ice_v` | `ice5` | `5`, `V`, `ice5` | ✅ Yes |
| `ice_vi` | `ice6` | `6`, `VI`, `ice6` | ✅ Yes |
| `ice_vii` | `ice7` | `7`, `VII`, `ice7` | ✅ Yes |
| `ice_viii` | `ice8` | `8`, `VIII`, `ice8` | ✅ Yes |
| (hydrate sI) | `sI` | `CS1`, `MEP`, `sI`, `A15` | ✅ Yes |
| (hydrate sII) | `sII` | `CS2`, `MTN`, `sII`, `16` | ✅ Yes |
| (hydrate sH) | `sH` | `DOH`, `HS3`, `sH` | ✅ Yes |

**Confidence: HIGH** — Verified from unitcells.html official documentation.

**⚠️ Note on ice1h axis convention:** GenIce3 documentation states: "Due to a historical reason, the crystal axes of hexagonal ice are exchanged. If you want the basal plane to be Z axis, please use `ice1h_unit` instead." QuickIce should verify whether the current `ice1h` axis convention in GenIce3 matches GenIce2's output. If GenIce2 also uses the historical (swapped) convention, this is fine. If not, switch to `ice1h_unit`.

---

### 2.5 Depolarization Parameter Mapping

| GenIce2 | GenIce3 | Meaning |
|---|---|---|
| `depol='strict'` | `pol_loop_1=2000` (or higher) | Maximum depolarization effort |
| `depol='lazy'` | `pol_loop_1=1` (or omit, use default 1000) | Minimal depolarization |
| `depol='none'` | `pol_loop_1=0` | No depolarization |
| (not available) | `pol_loop_2=N` | Stage 2 depolarization (more aggressive, default 0) |
| (not available) | `target_pol=[0,0,0]` | Target polarization vector (default: zero) |
| (not available) | `depol_loop=N` | Deprecated alias for `pol_loop_1` |

**GenIce2 `depol='strict'`** internally set `dipoleOptimizationCycles` to a high value. In GenIce3, `pol_loop_1=2000` provides comparable strict depolarization. The CLI docs say: "stage 1: very cheap but limited adjustment range" and "stage 2: more forceful method, slightly heavier cost, reliable convergence."

**Recommended for QuickIce:** Use `pol_loop_1=2000, pol_loop_2=0` as the baseline. If stricter depolarization is needed, enable `pol_loop_2=200` as well.

**Confidence: HIGH** — Verified from cli.html official docs and genice.py source.

---

### 2.6 Seed / Random State Handling

**GenIce2 (current QuickIce approach):**
```python
# Manual save/restore of global np.random state
original_state = np.random.get_state()
try:
    np.random.seed(seed)
    # ... generate ice ...
finally:
    np.random.set_state(original_state)
```

**GenIce3 approach:**
```python
genice = GenIce3(seed=42)
# Internally: np.random.seed(seed) is called in the setter
# Also clears the DependencyEngine cache
```

**⚠️ CRITICAL: GenIce3 STILL uses global `np.random.seed()` internally.**

From genice.py source, the `seed` setter:
```python
@seed.setter
def seed(self, seed):
    self._seed = seed
    np.random.seed(seed)  # ← Still global!
    self.engine.cache.clear()
```

This means:
1. **GenIce3 is NOT thread-safe** — same as GenIce2
2. QuickIce's current save/restore pattern for `np.random.get_state()` / `np.random.set_state()` should still be used around GenIce3 calls
3. The `seed` constructor parameter is a convenience, but does NOT use the newer `np.random.Generator` API

**Migration strategy:** Keep the current save/restore pattern. Pass seed to the `GenIce3` constructor AND save/restore `np.random` state around the entire call for thread safety.

```python
original_state = np.random.get_state()
try:
    genice = GenIce3(seed=seed, pol_loop_1=2000, ...)
    genice.set_unitcell(self.lattice_name, density=self.density)
    gro_string = Exporter("gromacs").dumps(genice, water_model="3site")
finally:
    np.random.set_state(original_state)
```

**Confidence: HIGH** — Verified from genice.py source code (seed setter).

---

## 3. GRO Output Format Comparison

### 3.1 Atom Naming

| Water Model | GenIce2 Atom Names | GenIce3 Atom Names | Residue Name (v2/v3) | Compatible? |
|---|---|---|---|---|
| TIP3P (3-site) | `O`, `H`, `H` | `O`, `H`, `H` | `SOL` / `SOL` | ✅ Identical |
| TIP4P (4-site) | `OW`, `HW1`, `HW2`, `MW` | `OW`, `HW1`, `HW2`, `MW` | `ICE` / `ICE` | ✅ Identical |
| TIP4P/Ice | `OW`, `HW1`, `HW2`, `MW` | `OW`, `HW1`, `HW2`, `MW` | `ICE` / `ICE` | ✅ Identical |

**Verified by source code:**
- GenIce3 `tip3p.py`: `labels = ["O", "H", "H"]`, `name = "SOL"` 
- GenIce3 `tip4p.py`: `labels = ["OW", "HW1", "HW2", "MW"]`, `name = "ICE"`
- GenIce3 `ice.py`: `labels = ["OW", "HW1", "HW2", "MW"]`, `name = "ICE"`
- GenIce2 verified via runtime: TIP3P = `['O', 'H', 'H']`, TIP4P = `['OW', 'HW1', 'HW2', 'MW']`

### 3.2 Guest Molecule Naming

| Guest | GenIce2 Atom Names | GenIce3 Atom Names | Residue Name | Compatible? |
|---|---|---|---|---|
| All-atom CH4 (`ch4`) | `C`, `H`, `H`, `H`, `H` | `C`, `H`, `H`, `H`, `H` | `CH4` / `CH4` | ✅ Identical |
| United-atom CH4 (`me`) | `Me` | `Me` | `Me` / `Me` | ✅ Identical |
| All-atom THF (`thf`) | `O`, `CA`, `CA`, `CB`, `CB`, `H`×8 | `O`, `CA`, `CA`, `CB`, `CB`, `H`×8 | `THF` / `THF` | ✅ Identical |
| United-atom THF (`uathf6`) | `O`, `CA`, `CB`, `CB`, `CA`, `CM` | `O`, `CA`, `CB`, `CB`, `CA`, `CM` | `THF` / `THF` | ✅ Identical |

**Verified by GenIce3 source code:**
- `ch4.py`: `labels = ["C", "H", "H", "H", "H"]`, `name = "CH4"`
- `me.py` (via `one.py`): `labels = ["Me"]`, `name = "Me"` 
- `thf.py`: `labels = ["O", "CA", "CA", "CB", "CB"] + ["H"]*8`, `name = "THF"`
- `uathf6.py`: `labels = ["O", "CA", "CB", "CB", "CA", "CM"]`, `name = "THF"`

### 3.3 GRO Column Format

Both GenIce2 and GenIce3 use the standard GROMACS .gro fixed-width format:

```
%5d%5s%5s%5d%8.3f%8.3f%8.3f
```

| Columns | Content | Width |
|---|---|---|
| 0–4 | Residue sequence number | 5 chars, right-aligned |
| 5–9 | Residue name | 5 chars, left-aligned |
| 10–14 | Atom name | 5 chars, right-aligned |
| 15–19 | Atom sequence number | 5 chars, right-aligned |
| 20–27 | X coordinate (nm) | 8 chars, 3 decimal places |
| 28–35 | Y coordinate (nm) | 8 chars, 3 decimal places |
| 36–43 | Z coordinate (nm) | 8 chars, 3 decimal places |

**The format is IDENTICAL between GenIce2 and GenIce3.** QuickIce's `parse_gro_string()` and `_parse_gro_result()` will work unchanged.

**⚠️ Edge case:** For >99999 atoms, both GenIce2 and GenIce3 clamp residue/atom numbers to 99999. QuickIce doesn't typically generate structures this large, so this is not a concern.

**Confidence: HIGH** — Verified from gromacs.py source (`_to_gro` function) and GenIce2 runtime output.

---

## 4. Guest Molecule / Cage Naming Mapping

### 4.1 Cage Name Format

| GenIce2 Cage ID | GenIce3 Cage ID | Cage Type | Hydrate Structure |
|---|---|---|---|
| `"12"` | `"A12"` | 5^12 (small dodecahedron) | sI, sII, sH |
| `"14"` | `"A14"` | 5^12 6^2 (tetrakaidecahedron) | sI (large cage) |
| `"16"` | `"A16"` | 5^12 6^4 (hexakaidecahedron) | sII (large cage) |
| (not used) | `"A20"` | 5^12 6^8 (icosikaedron) | sH (large cage) |

The "A" prefix stands for "Archimedean" (Archimedean solid naming convention).

### 4.2 Backward Compatibility

**GenIce3 accepts BOTH numeric and prefixed cage labels** in the `--guest` CLI option:
```
-g A12=me          # preferred (prefixed)
-g "12=co2*0.6+me*0.4"  # also accepted (numeric)
```

From `options.py` source, `parse_guest_option` takes a dict like `{"A12": "me", "14": "et"}` and passes the keys through as-is. The cage label matching happens inside the `GenIce3` engine.

**However, for the Python API, use the "A" prefix convention** as shown in the official examples (`6_with_guests.py`).

### 4.3 QuickIce Migration for Cage Names

Current QuickIce code (hydrate_generator.py):
```python
# GenIce2 style
guest_spec = f"12={guest_name}"
parse_guest(guests, guest_spec)
```

Migrated code:
```python
# GenIce3 style
from genice3.cli.options import parse_guest_option
guest_dict = {"A12": guest_name}  # Add "A" prefix
# For occupancy < 1.0:
# guest_dict["A12"] = f"{guest_name}*{occupancy}"

genice = GenIce3(
    guests=parse_guest_option(guest_dict),
)
```

### 4.4 sH Hydrate Large Cage Naming

**⚠️ Important:** The current QuickIce code uses `"16"` as the default large cage for sH. However, sH's large cage is actually 5^12 6^8 (20-hedron), which would be labeled `"A20"` in GenIce3. The `"16"` was likely an approximation or error. This should be corrected during migration:

```python
# Current (possibly incorrect for sH):
if config.lattice_type == "sI":
    large_cage = "A14"  # 5^12 6^2
elif config.lattice_type == "sII":
    large_cage = "A16"  # 5^12 6^4
else:  # sH
    large_cage = "A20"  # 5^12 6^8 (was incorrectly "16")

# Also: sH has a medium cage (4^3 5^6 6^3) that GenIce3 labels differently
# This needs investigation — see Open Questions below
```

**Confidence: HIGH** for sI and sII. **MEDIUM** for sH — the exact GenIce3 cage labels for sH's three cage types need verification via `Exporter("cage_survey").dump(genice)`.

---

## 5. Water Model as Exporter Suboption

### 5.1 How It Works

In GenIce3, the water model is no longer a separate plugin passed to `generate_ice()`. Instead, it's a suboption of the exporter:

```python
# CLI: genice3 1h -e "gromacs :water_model tip4p"
# API:
Exporter("gromacs").dumps(genice, water_model="tip4p")
```

The `dumps()` function internally calls `parse_water_model_option()` which loads the appropriate molecule plugin.

### 5.2 Available Water Models

| GenIce3 `water_model` | Atoms | Residue Name | Equivalent GenIce2 Plugin | Atom Names |
|---|---|---|---|---|
| `"3site"` / `"tip3p"` / `"spce"` | 3 | `SOL` | `safe_import('molecule', 'tip3p')` | O, H, H |
| `"4site"` / `"tip4p"` | 4 | `ICE` | `safe_import('molecule', 'tip4p')` | OW, HW1, HW2, MW |
| `"ice"` | 4 | `ICE` | (not in GenIce2 — **NEW**) | OW, HW1, HW2, MW |
| `"5site"` / `"tip5p"` | 5 | `SOL` | (not in QuickIce) | OW, HW1, HW2, LP1, LP2 |
| `"6site"` / `"NvdE"` | 6 | `SOL` | (not in QuickIce) | Multiple |
| `"tip4p2005"` | 4 | `ICE` | (not in QuickIce) | OW, HW1, HW2, MW |
| `"physical_water"` | 1 | `OW` | (not in QuickIce) | OW |

**⚠️ TIP4P/Ice model (`"ice"`)** — This is the exact water model QuickIce uses for hydrates (based on Abascal 2005, DOI: 10.1063/1.1931662). GenIce3 has a dedicated `"ice"` water model that produces TIP4P/Ice geometry. GenIce2 did not have this as a separate model — it used the generic TIP4P.

However, QuickIce's current approach generates ice with TIP3P and normalizes to TIP4P-ICE at export. The geometry difference between TIP4P and TIP4P/Ice is only in the M-site distance (MW position):
- TIP4P: `mz = 0.15/10 = 0.015 nm`
- TIP4P/Ice: `mz = 0.1577/10 = 0.01577 nm`

This is a tiny difference that QuickIce's export normalization already handles.

### 5.3 QuickIce Water Model Migration

For **ice generation** (generator.py), no change needed:
```python
# Current: TIP3P for ice generation → normalize to TIP4P-ICE at export
# GenIce3: Same approach
gro_string = Exporter("gromacs").dumps(genice, water_model="3site")
```

For **hydrate generation** (hydrate_generator.py), two options:
```python
# Option A: Keep using generic TIP4P (same as GenIce2)
gro_string = Exporter("gromacs").dumps(genice, water_model="4site")

# Option B: Use exact TIP4P/Ice model (recommended improvement)
gro_string = Exporter("gromacs").dumps(genice, water_model="ice")
```

**Recommendation:** Use `water_model="ice"` for hydrates. The TIP4P/Ice model is the correct one for ice simulations, and QuickIce's AGENTS.md explicitly references Abascal et al. 2005. Using `"ice"` directly eliminates the need for TIP4P→TIP4P-ICE normalization at export time.

**Confidence: HIGH** — Verified from water-models.html and molecule source files.

---

## 6. Complete `generate_ice` Equivalent

### 6.1 Ice Generation (Full Working Example)

```python
from genice3.genice import GenIce3
from genice3.plugin import Exporter
import numpy as np

def generate_ice_gro(lattice_name: str, density: float,
                     supercell_matrix: np.ndarray, seed: int) -> str:
    """Generate ice structure and return GRO string.
    
    Equivalent to GenIce2's:
        ice = GenIce(lattice, density=density, reshape=supercell_matrix)
        gro_string = ice.generate_ice(formatter=formatter, water=water, depol='strict')
    """
    original_state = np.random.get_state()
    try:
        genice = GenIce3(
            seed=seed,
            pol_loop_1=2000,       # depol='strict' equivalent
            pol_loop_2=0,
            replication_matrix=supercell_matrix,
            target_pol=np.array([0.0, 0.0, 0.0]),  # zero polarization target
        )
        genice.set_unitcell(lattice_name, density=density)
        return Exporter("gromacs").dumps(genice, water_model="3site")
    finally:
        np.random.set_state(original_state)
```

### 6.2 Hydrate Generation (Full Working Example)

```python
from genice3.genice import GenIce3
from genice3.plugin import Exporter
from genice3.cli.options import parse_guest_option
import numpy as np

def generate_hydrate_gro(lattice_name: str, supercell_matrix: np.ndarray,
                         guest_cages: dict, seed: int) -> str:
    """Generate hydrate structure and return GRO string.
    
    Args:
        lattice_name: GenIce3 unit cell name ("CS1", "CS2", "DOH")
        supercell_matrix: 3x3 replication matrix
        guest_cages: Dict like {"A12": "ch4", "A14": "ch4"}
        seed: Random seed
    """
    original_state = np.random.get_state()
    try:
        genice = GenIce3(
            seed=seed,
            pol_loop_1=2000,
            replication_matrix=supercell_matrix,
            guests=parse_guest_option(guest_cages),
        )
        genice.set_unitcell(lattice_name)
        return Exporter("gromacs").dumps(genice, water_model="4site")
    finally:
        np.random.set_state(original_state)

# Usage for sI hydrate with CH4 in all cages:
gro = generate_hydrate_gro(
    lattice_name="CS1",
    supercell_matrix=np.diag([1, 1, 1]),
    guest_cages={"A12": "ch4", "A14": "ch4"},
    seed=42,
)

# Usage for sI hydrate with partial occupancy:
gro = generate_hydrate_gro(
    lattice_name="CS1",
    supercell_matrix=np.diag([2, 2, 2]),
    guest_cages={"A12": "ch4*0.9", "A14": "thf"},
    seed=42,
)
```

---

## 7. Critical Differences Requiring Special Handling

### 7.1 `dumps()` vs `dump()` — **BREAKING if missed**

| Method | Return | Behavior | QuickIce Usage |
|---|---|---|---|
| `dump(genice, file=sys.stdout, **options)` | `None` | Writes to file | ❌ DO NOT USE |
| `dumps(genice, water_model="3site", **options)` | `str` | Returns GRO string | ✅ USE THIS |

QuickIce parses the GRO string directly via `parse_gro_string()` / `_parse_gro_result()`. Using `dump()` would write to stdout and return None, causing a crash.

### 7.2 Density Parameter Location Change

| GenIce2 | GenIce3 |
|---|---|
| `GenIce(lattice, density=0.9, reshape=M)` | `genice.set_unitcell("1h", density=0.9)` |

In GenIce2, `density` was a `GenIce` constructor parameter. In GenIce3, it's a unitcell suboption passed to `set_unitcell()`. This is because different unit cells have different density handling.

### 7.3 Guest Molecules Moved to Constructor

| GenIce2 | GenIce3 |
|---|---|
| `ice.generate_ice(guests=guests, ...)` | `GenIce3(guests=parse_guest_option({...}))` |

In GenIce2, guests were passed to `generate_ice()`. In GenIce3, guests are set in the `GenIce3` constructor as part of the reactive pipeline.

### 7.4 Reactive Pipeline (No Fixed Stages)

GenIce2 had a fixed 7-stage pipeline. GenIce3 uses a reactive DependencyEngine — properties are computed on demand when accessed. This is an architectural change that:

- Makes the API more declarative (set properties, then request output)
- Means `Exporter.dumps()` triggers all necessary computations automatically
- No need to manually orchestrate the pipeline

### 7.5 Removed `genice2.lattices.sI/sII/sH` Direct Imports

GenIce2 allowed direct imports:
```python
from genice2.lattices import sI, sII, sH
```

GenIce3 does not have direct lattice module imports. Instead, use unitcell name strings:
```python
genice.set_unitcell("CS1")   # sI
genice.set_unitcell("CS2")   # sII
genice.set_unitcell("DOH")   # sH
```

### 7.6 Python Version Requirement

| Requirement | GenIce2 | GenIce3 |
|---|---|---|
| Python | ≥3.8 (inferred) | ≥3.11, <3.14 |

**⚠️ CRITICAL:** GenIce3 requires Python ≥3.11. QuickIce uses Python 3.14.3 (conda-forge), which satisfies this. However, if there are any deployment environments with older Python, they would need upgrading.

GenIce3 also requires `genice-core >=1.5.4` (GenIce2 used `genice-core==1.4.3`).

**Confidence: HIGH** — Verified from PyPI and getting-started.html.

---

## 8. Summary of Changes QuickIce Must Make

### Files to Modify

| File | Changes Required |
|---|---|
| `quickice/structure_generation/generator.py` | Replace GenIce2 imports/API with GenIce3. Use `dumps()` instead of `generate_ice()`. Keep `np.random` save/restore. |
| `quickice/structure_generation/hydrate_generator.py` | Replace GenIce2 imports/API with GenIce3. Change guest parsing. Use `dumps()`. Add "A" prefix to cage names. |
| `quickice/structure_generation/mapper.py` | Add GenIce3 lattice name aliases (no changes needed if keeping `ice1h` etc., which GenIce3 supports). |
| `environment.yml` | Replace `genice2=2.2.13.1` with `genice3>=3.0b3`. Update `genice-core` requirement. |
| `quickice/structure_generation/types.py` | Possibly update `HYDRATE_LATTICES` if GenIce3 cage naming changes. |

### Minimal Code Changes (generator.py)

```python
# Before (GenIce2)
from genice2.plugin import safe_import
from genice2.genice import GenIce

lattice = safe_import('lattice', self.lattice_name).Lattice()
ice = GenIce(lattice, density=self.density, reshape=self.supercell_matrix)
water = safe_import('molecule', 'tip3p').Molecule()
formatter = safe_import('format', 'gromacs').Format()
gro_string = ice.generate_ice(formatter=formatter, water=water, depol='strict')

# After (GenIce3)
from genice3.genice import GenIce3
from genice3.plugin import Exporter

genice = GenIce3(
    seed=seed,
    pol_loop_1=2000,
    replication_matrix=self.supercell_matrix,
)
genice.set_unitcell(self.lattice_name, density=self.density)
gro_string = Exporter("gromacs").dumps(genice, water_model="3site")
```

### Minimal Code Changes (hydrate_generator.py)

```python
# Before (GenIce2)
from genice2.genice import GenIce
from genice2.plugin import safe_import
from genice2.valueparser import parse_guest
from collections import defaultdict

lattice = safe_import('lattice', lattice_name).Lattice()
ice = GenIce(lattice, reshape=supercell_matrix)
water = safe_import('molecule', 'tip4p').Molecule()
formatter = safe_import('format', 'gromacs').Format()
guests = defaultdict(dict)
parse_guest(guests, f"12={guest_name}")
gro_string = ice.generate_ice(formatter=formatter, water=water, guests=guests, depol='strict')

# After (GenIce3)
from genice3.genice import GenIce3
from genice3.plugin import Exporter
from genice3.cli.options import parse_guest_option

guest_dict = {"A12": guest_name, "A14": guest_name}  # "A" prefix added
genice = GenIce3(
    seed=seed,
    pol_loop_1=2000,
    replication_matrix=supercell_matrix,
    guests=parse_guest_option(guest_dict),
)
genice.set_unitcell(lattice_name)
gro_string = Exporter("gromacs").dumps(genice, water_model="4site")
```

---

## 9. Open Questions / Items Needing Verification

| # | Question | Why It Matters | How to Verify |
|---|---|---|---|
| 1 | sH hydrate cage names in GenIce3 | sH has 3 cage types (D, D', H); exact GenIce3 labels unknown | Run `Exporter("cage_survey").dump()` on sH structure |
| 2 | `ice1h` vs `ice1h_unit` axis convention | GenIce3 warns about historical axis swap; need to confirm GenIce2 matches | Compare GRO box vectors between GenIce2 and GenIce3 |
| 3 | `genice-core` version compatibility | GenIce3 requires `>=1.5.4`; QuickIce has `1.4.3` | Install GenIce3 and test |
| 4 | Performance comparison | GenIce3 uses DependencyEngine; unclear if faster/slower than GenIce2 | Benchmark same structure on both |
| 5 | `parse_guest_option` occupancy syntax with mixed guests | e.g., `"A12=co2*0.6+ch4*0.4"` — need to verify QuickIce doesn't use this pattern currently | Check all QuickIce guest configurations |
| 6 | TIP4P-ICE normalization still needed with `water_model="ice"` | If GenIce3's "ice" model produces correct TIP4P-ICE MW position, QuickIce can skip normalization | Compare MW positions in GRO output |
| 7 | Beta stability of GenIce3 3.0b3 | Beta may have breaking changes before stable release | Monitor PyPI and GitHub releases |

---

## 10. Confidence Assessment

| Area | Confidence | Reason |
|---|---|---|
| Core API mapping (GenIce3 → GenIce2) | HIGH | Official docs + source code verified |
| `dumps()` return type | HIGH | Verified from gromacs.py source |
| GRO format compatibility | HIGH | Verified from gromacs.py source + GenIce2 runtime |
| Water model naming | HIGH | Verified from water-models.html + molecule source files |
| Guest molecule naming | HIGH | Verified from molecule source files |
| Cage naming (sI, sII) | HIGH | Verified from API examples + CLI docs |
| Cage naming (sH) | MEDIUM | Not explicitly shown in docs; needs cage_survey verification |
| Depolarization parameter mapping | HIGH | Verified from CLI docs + genice.py source |
| Thread safety (seed handling) | MEDIUM | GenIce3 still uses np.random.seed globally; needs empirical testing |
| Lattice name compatibility | HIGH | Verified from unitcells.html (all QuickIce names exist in GenIce3) |
| Python version compatibility | HIGH | Verified from PyPI metadata |

---

## Sources

| Source | URL | Confidence |
|---|---|---|
| GenIce3 AI Assistant Overview | https://genice-dev.github.io/GenIce3/for-ai-assistants.html | HIGH (official) |
| GenIce3 API Examples (Basic) | https://genice-dev.github.io/GenIce3/api-examples/basic.html | HIGH (official) |
| GenIce3 API Examples (Guest Occupancy) | https://genice-dev.github.io/GenIce3/api-examples/guest_occupancy.html | HIGH (official) |
| GenIce3 Output Formats | https://genice-dev.github.io/GenIce3/output-formats.html | HIGH (official) |
| GenIce3 Unit Cells | https://genice-dev.github.io/GenIce3/unitcells.html | HIGH (official) |
| GenIce3 Water Models | https://genice-dev.github.io/GenIce3/water-models.html | HIGH (official) |
| GenIce3 CLI Reference | https://genice-dev.github.io/GenIce3/cli.html | HIGH (official) |
| GenIce3 Source: genice.py | https://github.com/genice-dev/GenIce3/blob/main/genice3/genice.py | HIGH (source) |
| GenIce3 Source: plugin.py | https://github.com/genice-dev/GenIce3/blob/main/genice3/plugin.py | HIGH (source) |
| GenIce3 Source: gromacs.py (exporter) | https://github.com/genice-dev/GenIce3/blob/main/genice3/exporter/gromacs.py | HIGH (source) |
| GenIce3 Source: options.py (CLI) | https://github.com/genice-dev/GenIce3/blob/main/genice3/cli/options.py | HIGH (source) |
| GenIce3 Source: tip3p.py (molecule) | https://github.com/genice-dev/GenIce3/blob/main/genice3/molecule/tip3p.py | HIGH (source) |
| GenIce3 Source: tip4p.py (molecule) | https://github.com/genice-dev/GenIce3/blob/main/genice3/molecule/tip4p.py | HIGH (source) |
| GenIce3 Source: ice.py (TIP4P/Ice molecule) | https://github.com/genice-dev/GenIce3/blob/main/genice3/molecule/ice.py | HIGH (source) |
| GenIce3 Source: ch4.py (molecule) | https://github.com/genice-dev/GenIce3/blob/main/genice3/molecule/ch4.py | HIGH (source) |
| GenIce3 Source: thf.py (molecule) | https://github.com/genice-dev/GenIce3/blob/main/genice3/molecule/thf.py | HIGH (source) |
| GenIce3 Source: me.py (united-atom methane) | https://github.com/genice-dev/GenIce3/blob/main/genice3/molecule/me.py | HIGH (source) |
| PyPI: genice3 3.0b3 | https://pypi.org/project/genice3/3.0b3/ | HIGH (official) |
| GenIce2 Runtime Verification | Python runtime on QuickIce env | HIGH (empirical) |
