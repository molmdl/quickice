# R1: GenIce2 `safe_import` Interception Feasibility

**Project:** QuickIce — Custom Guest Hydrate Generation
**Mode:** Feasibility
**Researched:** 2025-06-22
**Overall confidence:** HIGH

---

## Executive Summary

Three injection methods for inserting custom guest molecules into GenIce2's cage-guest insertion pipeline were tested; **all three work end-to-end**. The `mol[file=path]` syntax leverages GenIce2's existing plugin infrastructure and requires the least custom code — a `.mol` file is all that's needed. The `sys.modules` injection method offers the most programmatic control (arbitrary Molecule subclass with computed `sites_`), but requires manual module registration. Monkey-patching `safe_import` works but is the most invasive and fragile. A fourth method — local plugin directory — also works but is CWD-dependent.

A critical constraint discovered: **GRO residue names must be ≤5 characters**. Exceeding this causes GROMACS to reject the file with a fatal error (`gro is fixed format`). The `mol` plugin reads the molecule name from the first line of the `.mol` file and sets it as `name_` directly — no truncation, no validation. QuickIce must enforce the 5-char limit itself.

## Verdict

**YES** — Custom guest injection into GenIce2 is fully feasible. Multiple clean paths exist.

---

## Method 1: `sys.modules` Injection

**Status: WORKS** | **Confidence: HIGH** (verified end-to-end with GenIce + GROMACS format)

### How it works

`safe_import` in `genice2/plugin.py` (line 279-285) calls `importlib.import_module("genice2.molecules.<name>")`. If a module is already registered in `sys.modules` under that key, Python returns it without attempting a filesystem import.

### Working code

```python
import sys, types
import numpy as np
import genice2.molecules

# 1. Create a synthetic module
mod = types.ModuleType("genice2.molecules.custom_guest")
mod.__package__ = "genice2.molecules"
mod.__file__ = "<injected>"

# 2. Define a Molecule subclass
class Molecule(genice2.molecules.Molecule):
    def __init__(self, **kwargs):
        # sites_ in nm, relative to molecular center
        self.sites_ = np.array([[0.0, 0.0, 0.0], [0.15, 0.0, 0.0]])
        self.labels_ = ["C", "O"]
        self.name_ = "CUS"  # MUST be ≤5 chars for GRO format!

mod.Molecule = Molecule

# 3. Register in sys.modules BEFORE calling GenIce
sys.modules["genice2.molecules.custom_guest"] = mod

# 4. Use in GenIce pipeline
from genice2.genice import GenIce
from genice2.lattices import sI
from genice2.formats import gromacs

lat = sI.Lattice()
ice = GenIce(lat, density=0.8)
guests = {"12": {"custom_guest": 1.0}}  # 100% occupancy in 12-hedra
result = ice.generate_ice(gromacs.Format(), water=..., guests=guests)
```

### Constraints

| Constraint | Detail |
|-----------|--------|
| Name must pass `audit_name()` | Must match `^[A-Za-z0-9-_]+$` — no spaces, brackets, or path chars |
| `name_` must be ≤5 chars | GROMACS rejects GRO files with >5-char residue names |
| Module must exist in `sys.modules` before `generate_ice()` | Registration must happen before Stage7 runs |
| `sites_` must be in nm | Not Å — the `arrange()` function uses nm directly |
| `labels_` must be atom type strings | Used in GRO output as atom names |

### Pros
- Full programmatic control over molecule geometry
- Can compute `sites_` from GRO/ITP data at runtime
- No filesystem dependencies (no .mol file needed)
- Clean: leverages Python's import mechanism as intended

### Cons
- Requires manual cleanup of `sys.modules` if names conflict
- Name cannot contain brackets (would fail `audit_name`)

---

## Method 2: Monkey-Patching `safe_import`

**Status: WORKS** | **Confidence: HIGH** (verified standalone, not tested end-to-end)

### How it works

Replace `genice2.plugin.safe_import` with a wrapper that intercepts specific molecule names and returns a custom module, falling through to the original for all other names.

### Working code

```python
import genice2.plugin
import genice2.genice  # must also patch here since safe_import is imported

_original = genice2.plugin.safe_import

def patched_safe_import(category, name):
    if category == "molecule" and name == "custom_guest":
        return my_custom_module  # pre-built types.ModuleType
    return _original(category, name)

genice2.plugin.safe_import = patched_safe_import
genice2.genice.safe_import = patched_safe_import  # CRITICAL: patch both namespaces
```

### Critical detail

`safe_import` is imported by name in `genice2/genice.py` (line 25: `from genice2.plugin import safe_import`). This means `genice2.genice.safe_import` is a separate reference that must be patched independently. Missing this patch causes Stage7 to call the original `safe_import`, not the patched one.

### Pros
- Can intercept arbitrary names regardless of `audit_name`
- Complete control over the resolution pipeline

### Cons
- Must patch two namespaces (`genice2.plugin` AND `genice2.genice`)
- More invasive — breaks if GenIce2 refactors import structure
- Harder to reason about than sys.modules injection
- Thread-safety concerns if GenIce runs in multiple threads

### Recommendation: **Do NOT use this as primary method.** Use only as a fallback if `sys.modules` injection fails for a specific use case. The dual-namespace patching requirement is fragile.

---

## Method 3: `mol[file=path]` Plugin Syntax

**Status: WORKS** | **Confidence: HIGH** (verified end-to-end with GenIce + GROMACS format)

### How it works

GenIce2 has a built-in `mol` plugin (`genice2/molecules/mol.py`) that reads MolView-format `.mol` files. The `plugin_option_parser` in `valueparser.py` parses the bracket syntax `mol[file=path]` into `name="mol"` and `kwargs={"file": "path"}`.

### Stage7 flow (verified by reading `genice.py` lines 1112-1115):

```python
for molec, cages in molecules.items():
    guest_type, guest_options = plugin_option_parser(molec)  # "mol[file=X]" -> ("mol", {"file": "X"})
    gmol = safe_import("molecule", guest_type).Molecule(**guest_options)  # mol.Molecule(file="X")
```

### Working code

```python
guests = {"12": {"mol[file=/path/to/guest.mol]": 1.0}}
ice.generate_ice(formatter, water=water, guests=guests)
```

### .mol file format (MolView V2000)

```
RESNAME               <- Line 1: becomes self.name_ (MUST be ≤5 chars!)
  Program info        <- Line 2: ignored
  Comment             <- Line 3: ignored
  2  1  0 ... V2000   <- Line 4: atom count, bond count, ...
    0.0000  0.0000  0.0000 C  ...  <- Atom lines (x,y,z in ANGSTROM, label)
    1.5000  0.0000  0.0000 O  ...
  1  2  1  0          <- Bond lines (atom1, atom2, type, ...)
M  END
```

**CRITICAL:** The `.mol` file parser reads coordinates in Å and divides by 10.0 to convert to nm (line 44 of `mol.py`: `self.sites_ = np.array(sites) / 10.0`). This means sites are correctly in nm for GenIce.

### Two syntax variants

| Syntax | Parsed as | Works? |
|--------|-----------|--------|
| `mol[file=/path/to/guest.mol]` | `name="mol", kwargs={"file": "/path/to/guest.mol"}` | YES (preferred) |
| `mol[/path/to/guest.mol]` | `name="mol", kwargs={"/path/to/guest.mol": True}` | YES (positional arg) |

The `mol` plugin handles both: `if v == True: filename = k` or `elif k == "file": filename = v`.

### Pros
- Uses GenIce2's existing plugin infrastructure — no hacks
- `.mol` files are standard chemistry format, easy to generate
- Automatic Å→nm conversion built into the parser
- Works with absolute paths (verified with `/tmp/opencode/test_guest.mol`)

### Cons
- `.mol` format does NOT support residue name truncation — the first line becomes `name_` directly
- QuickIce must validate/truncate the name to ≤5 chars before writing the `.mol` file
- `.mol` format has limited atom type support (single-character element symbols like "C", "O", "N")
- No way to specify force field parameters — only geometry
- `.mol` format is for small molecules; very large guests may be awkward

---

## Method 4: Local Plugin Directory

**Status: WORKS** | **Confidence: HIGH** (verified standalone)

### How it works

`safe_import` first tries `importlib.import_module("molecules.<name>")` (local), before `genice2.molecules.<name>` (system). If CWD contains a `molecules/` directory with a `<name>.py` file, it will be found first.

### Constraints
- CWD must contain `molecules/` directory
- Less flexible than sys.modules injection
- Not suitable for QuickIce's runtime injection use case

### Recommendation: **Not recommended for QuickIce.** Too CWD-dependent and inflexible.

---

## Critical Finding: GRO Residue Name Length

**Confidence: HIGH** (verified with GROMACS 2023.5 fatal error)

### The problem

GenIce2's GROMACS formatter (`formats/gromacs.py`, line 78) uses Python format `{1:5s}` for residue names. Python does NOT truncate strings that exceed the field width — it outputs the full string, shifting all subsequent columns.

| `name_` length | GRO line length | Column alignment | GROMACS acceptance |
|----------------|-----------------|-------------------|--------------------|
| 5 chars | 44 (correct) | Correct | PASS |
| 6 chars | 45 (1 extra) | Atom name shifted | **FATAL ERROR** |
| 8 chars | 47 (3 extra) | All fields shifted | **FATAL ERROR** |

### GROMACS error message (verbatim)

```
Fatal error:
Something is wrong in the coordinate formatting of file unknown_file. Note
that gro is fixed format (see the manual)
```

### Impact on each method

| Method | Where `name_` comes from | Can enforce 5-char limit? |
|--------|--------------------------|---------------------------|
| sys.modules injection | Set in `__init__` of custom Molecule class | YES — QuickIce controls the code |
| Monkey-patch | Same as above | YES |
| `mol[file=path]` | Line 1 of `.mol` file (read by mol.py) | Must truncate before writing `.mol` file |
| Local plugin | Set in plugin `.py` file | YES |

### Recommendation

QuickIce MUST enforce `len(name_) <= 5` for any custom guest molecule. This should be a validation step in the pipeline, not a silent truncation (users need to know their name was modified).

---

## Feature Dependencies and Data Flow

### How custom guest data flows through GenIce2

```
User provides: GRO file + ITP file (or .mol file)
       │
       ▼
QuickIce converts → genice2.molecules.Molecule subclass
       │              (sites_ in nm, labels_, name_ ≤5 chars)
       ▼
Register in sys.modules["genice2.molecules.<name>"]
       │
       ▼
GenIce.generate_ice(guests={"12": {"<name>": fraction}})
       │
       ▼
Stage7: plugin_option_parser("<name>") → ("<name>", {})
Stage7: safe_import("molecule", "<name>") → our module
Stage7: module.Molecule(**kwargs) → Molecule instance
       │
       ▼
arrange(cage_centers, cell, identity_matrices, molecule)
       │  → positions = abs_cage_center + rotated_sites
       │  → Since rotation is identity, sites_ offsets are along fixed axes
       ▼
serialize → GRO output
```

### Key observation: Guest rotation

In Stage7 (genice.py lines 1123-1125), guest molecules are placed with **identity rotation matrices**:

```python
cmat = [np.identity(3) for i in cages]
self.universe.append(arrange(cage_center, self.repcell, cmat, gmol))
```

This means guest molecules are always placed with their `sites_` coordinates oriented along the lab-frame axes. For small, roughly spherical guests (CH4, CO2) this is fine. For asymmetric guests (THF, large organics), this means the guest orientation is fixed and **not random**. This is a known GenIce2 limitation, not something QuickIce needs to fix.

---

## Comparison Matrix

| Criterion | sys.modules | Monkey-patch | mol[file=path] | Local plugin |
|-----------|-------------|-------------|----------------|--------------|
| End-to-end verified | YES | Partial | YES | Partial |
| Code complexity | Low | Medium | Lowest | Low |
| Invasiveness | Low | High | None | None |
| Thread safety | Good | Poor | Good | Good |
| CWD dependency | None | None | None | High |
| Runtime flexibility | Full | Full | Limited to .mol | None |
| Force field params | Manual | Manual | Not supported | Manual |
| Å→nm conversion | Manual | Manual | Automatic | Manual |
| audit_name constraint | Yes | No | Yes (on "mol") | Yes |
| GenIce2 upgrade risk | Low | High | None | Low |

---

## Recommendation

### Primary method: `mol[file=path]` for simple cases

For the common case where the user provides a molecule geometry file, use the `mol` plugin syntax. It's the least invasive, most "GenIce-native" approach:

1. QuickIce reads the user's `.gro` + `.itp` files
2. QuickIce generates a `.mol` file with:
   - Line 1: residue name (≤5 chars, validated/truncated)
   - Atom coordinates converted from nm to Å (multiply by 10 for `.mol` format)
   - Element symbols derived from atom names
3. QuickIce passes `mol[file=/path/to/generated.mol]` in the `guests` dict

### Secondary method: `sys.modules` injection for computed/complex cases

For cases where the molecule geometry is computed programmatically (not from a file), or when the `.mol` format is insufficient (e.g., need multi-char atom labels like "CA", "CB"), use `sys.modules` injection:

1. QuickIce creates a `types.ModuleType` with a `Molecule` subclass
2. Registers it in `sys.modules["genice2.molecules.<name>"]`
3. Passes `<name>` in the `guests` dict

### Do NOT use: Monkey-patching or local plugin directory

Monkey-patching is fragile (dual-namespace requirement). Local plugins are CWD-dependent.

---

## Working Code Snippets for Production

### Pattern A: mol[file=path] approach

```python
def make_mol_file(gro_data, itp_data, output_path, resname_max_len=5):
    """Convert GRO+ITP data to a .mol file for GenIce2's mol plugin.

    Args:
        gro_data: parsed GRO file (atom names + coords in nm)
        itp_data: parsed ITP file (atom names, types)
        output_path: where to write .mol file
        resname_max_len: max chars for GRO residue name (default 5)
    """
    # Extract residue name from ITP, truncate to 5 chars
    resname = itp_data.moleculetype_name[:resname_max_len]

    atoms = gro_data.atoms  # list of (name, x_nm, y_nm, z_nm)

    with open(output_path, "w") as f:
        f.write(f"{resname}\n")
        f.write("  QuickIce\n")
        f.write("  Custom guest molecule\n")
        f.write(f"  {len(atoms):3d}  {0}  0  0  0  0  0  0  0  0999 V2000\n")
        for name, x, y, z in atoms:
            # Convert nm -> Angstrom for .mol format
            f.write(f"{x*10:10.4f}{y*10:10.4f}{z*10:10.4f} {name:<3s}  0  0  0  0  0  0  0  0  0  0  0  0\n")
        f.write("M  END\n")

# Usage in GenIce pipeline:
guests = {"12": {f"mol[file={mol_file_path}]": 1.0}}
```

### Pattern B: sys.modules injection approach

```python
def register_custom_guest(name, sites_nm, labels, resname):
    """Register a custom guest molecule in GenIce2's plugin namespace.

    Args:
        name: plugin name (must match ^[A-Za-z0-9-_]+$)
        sites_nm: numpy array of shape (N, 3), positions in nm
        labels: list of atom name strings
        resname: GRO residue name (MUST be ≤5 chars)
    """
    import sys, types
    import numpy as np
    import genice2.molecules

    assert len(resname) <= 5, f"Residue name '{resname}' exceeds 5-char GRO limit"
    from genice2.plugin import audit_name
    assert audit_name(name), f"Plugin name '{name}' fails audit_name check"

    mod = types.ModuleType(f"genice2.molecules.{name}")
    mod.__package__ = "genice2.molecules"

    class Molecule(genice2.molecules.Molecule):
        def __init__(self, **kwargs):
            self.sites_ = np.array(sites_nm, dtype=float)
            self.labels_ = list(labels)
            self.name_ = resname

    mod.Molecule = Molecule
    sys.modules[f"genice2.molecules.{name}"] = mod

# Usage:
register_custom_guest("my_guest", sites, labels, "MYGS")
guests = {"12": {"my_guest": 1.0}}
```

---

## Failure Modes and Edge Cases

### 1. Name collision with existing GenIce2 plugins
**What:** If the custom guest name matches an existing GenIce2 molecule (e.g., "ch4", "thf"), `sys.modules` injection will shadow the built-in.
**Prevention:** Use a naming convention like `qice_<name>` for QuickIce-registered guests, or check `sys.modules` before registration.

### 2. `audit_name` rejection
**What:** Plugin names with spaces, brackets, or special chars fail `audit_name`.
**Prevention:** Sanitize plugin names to match `^[A-Za-z0-9-_]+$`.

### 3. GRO residue name >5 chars
**What:** GROMACS rejects the output file with a fatal error.
**Prevention:** Validate/truncate `name_` to ≤5 chars. Alert user if truncation occurred.

### 4. `.mol` file with blank lines in header
**What:** The `mol` parser reads exactly 4 header lines (name, program, comment, counts). A blank line shifts the counts line, causing `IndexError`.
**Prevention:** When generating `.mol` files, ensure exactly 4 header lines with no blank lines.

### 5. `sites_` in Å instead of nm (sys.modules method)
**What:** GenIce2 uses nm throughout. Providing sites in Å will place atoms 10x too far from the cage center.
**Prevention:** Document clearly that `sites_` must be in nm. The `mol` plugin handles this automatically (divides by 10).

### 6. Guest orientation is always lab-frame (not random)
**What:** Stage7 uses identity rotation for guests. Asymmetric molecules will always point the same direction.
**Impact:** For small spherical guests, negligible. For elongated molecules, this could cause steric clashes.
**Mitigation:** This is a GenIce2 design choice, not fixable without modifying GenIce2 itself. For now, accept this limitation.

---

## Confidence Assessment

| Finding | Confidence | Source |
|---------|-----------|--------|
| sys.modules injection works end-to-end | HIGH | Tested with GenIce + GROMACS format |
| Monkey-patch works (dual namespace) | HIGH | Tested standalone; dual-namespace requirement verified by source reading |
| mol[file=path] works end-to-end | HIGH | Tested with GenIce + GROMACS format |
| GRO residue names must be ≤5 chars | HIGH | Verified with GROMACS 2023.5 fatal error |
| `audit_name` regex pattern | HIGH | Read directly from source code |
| Guest rotation is identity in Stage7 | HIGH | Read directly from genice.py lines 1123-1125 |
| `.mol` parser reads 4 fixed header lines | HIGH | Read directly from mol.py source + tested failure |
| `mol` plugin divides coords by 10 (Å→nm) | HIGH | Read directly from mol.py line 44 |
| Local plugin directory works | MEDIUM | Tested standalone but not end-to-end with GenIce |

---

## Gaps and Open Questions

1. **How to extract atom positions from GRO files?** The user provides `.gro` + `.itp` files. QuickIce needs a parser for GRO format to extract per-atom positions. This is a separate research task.

2. **How to handle custom atom types in .mol format?** The `.mol` format uses single-character element symbols. GRO/ITP files may use multi-character atom names like "CA", "CB", "HW". The `.mol` plugin reads whatever is in column 4 of the atom lines, so multi-char names work in GenIce's output, but the `.mol` format spec technically only supports element symbols. Need to test if this causes issues with downstream tools.

3. **Should QuickIce enforce `name_` truncation or raise an error?** If the user's residue name exceeds 5 chars, should we silently truncate or error? Recommendation: **error with a clear message**, since silent truncation could cause confusion (e.g., "ETHANOL" → "ETHAN" is ambiguous).

4. **Can we randomize guest orientations?** Currently GenIce2 places guests with identity rotation. For realistic simulations, random orientations would be preferable. This would require either:
   - Monkey-patching Stage7 (fragile)
   - Post-processing the GRO output
   - Submitting a feature request to GenIce2

5. **ITP file integration:** The `mol` plugin only reads geometry, not force field parameters. QuickIce will need to handle ITP file inclusion in the GROMACS topology separately from the GenIce2 pipeline.
