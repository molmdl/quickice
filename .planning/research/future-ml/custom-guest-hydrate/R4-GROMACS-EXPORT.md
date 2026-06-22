# R4: GROMACS Export for Custom Hydrate Guest

**Domain:** GROMACS topology file generation for user-provided custom guest molecules in clathrate hydrate structures  
**Researched:** 2026-06-22  
**Overall confidence:** HIGH (all findings from source code, no external dependencies)

---

## Table of Contents

1. [Current Hydrate Export Pipeline](#1-current-hydrate-export-pipeline)
2. [ITP Validation Requirements for Custom Guests](#2-itp-validation-requirements-for-custom-guests)
3. [Atomtypes Merging Strategy for .top Files](#3-atomtypes-merging-strategy-for-top-files)
4. [GRO Residue Name Length Constraints](#4-gro-residue-name-length-constraints)
5. [comb-rule=2 Compatibility Validation](#5-comb-rule2-compatibility-validation)
6. [Example: Converting etoh.itp to Hydrate Guest Format (ETH_H)](#6-example-converting-etohitp-to-hydrate-guest-format-eth_h)
7. [Confidence Assessment](#7-confidence-assessment)
8. [Blockers and Open Questions](#8-blockers-and-open-questions)

---

## 1. Current Hydrate Export Pipeline

### Step-by-step flow

The hydrate export pipeline operates through multiple writer functions in `gromacs_writer.py`, each producing a `.gro` + `.top` pair. The pipeline varies by which tabs are active:

#### 1a. Interface-only export (Tab 2 → Export)

Functions: `write_interface_gro_file()` + `write_interface_top_file()`

1. **Ice molecules** → SOL residue, 3 input atoms (O, H, H) expanded to 4 (OW, HW1, HW2, MW) via `compute_mw_position()`
2. **Water molecules** → SOL residue, 4 atoms pass-through (OW, HW1, HW2, MW)
3. **Guest molecules** → Detected by `detect_guest_type_from_atoms()`, residue name from `get_hydrate_guest_residue_name()`, written with native atom types
4. **Atom ordering**: Guests are reordered via `reorder_guest_atoms()` to match `.itp` canonical order (e.g., CH4: C-first instead of GenIce2's H-first)

In the `.top` file:
- `[ defaults ]`: comb-rule=2, nbfunc=1, gen-pairs=yes, fudgeLJ=0.5, fudgeQQ=0.8333
- `[ atomtypes ]`: OW_ice, HW_ice, MW (water) + guest-specific GAFF2 types (hardcoded)
- `#include "tip4p-ice.itp"`: Water molecule definition
- `#include "{guest_type}_hydrate.itp"`: Guest molecule definition (e.g., `ch4_hydrate.itp`)
- `[ molecules ]`: `SOL  {total_sol}` then `CH4_H  {guest_count}`

**Confidence: HIGH** — Directly from `write_interface_top_file()` lines 1001-1109

#### 1b. Ion export (Tab 5 → Export)

Functions: `write_ion_gro_file()` + `write_ion_top_file()`

Molecule order: SOL (ice+water) → guest → custom → solute → NA → CL

Same patterns as interface export, plus:
- Custom molecule atomtypes parsed from user's `.itp` via `parse_itp_atomtypes()` with deduplication
- Solute uses `_liquid.itp` (e.g., `ch4_liquid.itp`) with `_L` suffix
- Ion atomtypes (NA, CL) from Madrid2019 model

**Confidence: HIGH** — Directly from `write_ion_top_file()` lines 1747-1961

#### 1c. Custom molecule export (Tab 3 → Export)

Functions: `write_custom_molecule_gro_file()` + `write_custom_molecule_top_file()`

Molecule order: SOL (ice+water) → guest → custom

Key: Custom molecule atomtypes are parsed from user `.itp` file with deduplication against already-written types (Bug 3 fix pattern).

**Confidence: HIGH** — Directly from `write_custom_molecule_top_file()` lines 2192-2322

### Current ITP file pattern (bundled guests)

The codebase maintains **three ITP variants** per built-in guest:

| File | `[moleculetype]` name | Residue name in `[ atoms ]` | Usage context |
|------|----------------------|---------------------------|---------------|
| `ch4.itp` | `ch4` | `CH4` | Standalone CH4 reference |
| `ch4_hydrate.itp` | `CH4_H` | `CH4_H` | **Hydrate cage guest** (Tab 2/5 export) |
| `ch4_liquid.itp` | `CH4_L` | `CH4_L` | **Liquid solute** (Tab 4/5 export) |

Same pattern for THF: `thf.itp` → `thf_hydrate.itp` / `thf_liquid.itp`.

**All bundled hydrate ITPs have `[atomtypes]` commented out** (prefixed with `;`), with the header comment:
```
; Modified for QuickIce: [atomtypes] commented - types defined in main .top file
```

This is applied by `comment_out_atomtypes_in_itp()` at export time. The atomtypes are instead written directly into the main `.top` file's `[ atomtypes ]` section.

**Confidence: HIGH** — Verified by reading `ch4_hydrate.itp`, `thf_hydrate.itp`, `ch4_liquid.itp`, `thf_liquid.itp`, `ch4.itp`, `thf.itp`

### How the .top `[molecules]` section lists guests

The `[molecules]` section must list molecule types in the **exact same order** as they appear in the `.gro` file. This is a GROMACS requirement — it uses this section to know how to group consecutive atoms into molecules.

Current pattern (from `write_interface_top_file()`):
```
[ molecules ]
; Compound    #mols
SOL          {ice_count + water_count}
CH4_H        {guest_count}          ; or THF_H, etc.
```

For custom hydrate guests, the entry would be:
```
ETH_H        {guest_count}          ; e.g., ethanol hydrate guest
```

**Confidence: HIGH** — GROMACS standard requirement; verified in code

### How the .gro file formats guest residue names

The `.gro` format uses `%5s` left-justified for residue names (see line 856: `{guest_res_name:<5s}`). Current hydrate guests use:
- `CH4_H` (5 chars — exactly at the limit)
- `THF_H` (5 chars — exactly at the limit)

**Confidence: HIGH** — Directly from code format strings

---

## 2. ITP Validation Requirements for Custom Guests

### Complete validation checklist

When a user provides a custom `.itp` file for a hydrate guest, it must satisfy **all** of the following:

#### 2a. `[moleculetype]` name must get `_H` suffix

- **Requirement**: The `[moleculetype]` name in the hydrate guest ITP must end with `_H`
- **Example**: User provides `etoh.itp` with `[moleculetype] etoh 3` → must become `[moleculetype] ETH_H 3`
- **Why**: Distinguishes hydrate cage guests from liquid solutes (`_L`) and avoids collision with base names. Enforced by `MoleculetypeRegistry.register_hydrate_guest()`
- **Implementation**: Need to **rewrite** the `[moleculetype]` name and all residue names in the `[ atoms ]` section when generating the hydrate variant ITP

**Confidence: HIGH** — Pattern established by `ch4_hydrate.itp` and `thf_hydrate.itp`

#### 2b. `[atomtypes]` section: must be commented out or absent

- **Requirement**: The hydrate guest ITP must **NOT** have an active `[atomtypes]` section
- **Current pattern**: Bundled ITPs have `[atomtypes]` commented out with `;` prefix
- **Why**: GROMACS requires all atomtypes to be in the main `.top` file, before `#include` directives. Duplicate atomtype definitions in included ITPs cause fatal errors
- **Implementation**: Use `comment_out_atomtypes_in_itp()` (already exists, lines 316-360) to process user's ITP

**Confidence: HIGH** — Existing function handles this; established pattern

#### 2c. `comb-rule=2` (Lorentz-Berthelot): All atomtypes must use sigma/epsilon format

- **Requirement**: Every atomtype definition must use the **sigma/epsilon** column format, NOT the A/B format
- **Sigma/epsilon format** (8 columns, what QuickIce uses):
  ```
  name  bond_type  at.num  mass  charge  ptype  sigma(nm)  epsilon(kJ/mol)
  c3    c3        6       12.01 0.0     A      3.39771e-1  4.51035e-1
  ```
- **A/B format** (incompatible with comb-rule=2):
  ```
  name  bond_type  at.num  mass  charge  ptype  A(kJ·nm⁶/mol)  B(kJ·nm¹²/mol)
  ```
  In A/B format, columns 7-8 contain C6 and C12 Buckingham parameters, not sigma/epsilon. Using these with comb-rule=2 would produce **completely wrong** LJ interactions.

**Detection approach**:
1. Parse the `[atomtypes]` header comment — if it says "A" and "B" or "C6" and "C12", it's A/B format
2. Check numeric values — sigma values for organic atoms are typically 0.2–0.5 nm; A values are typically 10⁶–10⁸ scale (very large numbers). If column 7 value > 100, it's likely A/B format (not sigma in nm)
3. Check the `ptype` column — both formats use `A` for atom, so this alone isn't diagnostic

**Validation rule**: If any atomtype line has a column-7 value > 10 (which cannot be a sigma in nm for any physical atom), REJECT the ITP with an error message explaining the comb-rule=2 incompatibility.

**Confidence: HIGH** — Well-established GROMACS convention; verified from all bundled ITPs

#### 2d. GRO residue name limit: 5 characters max

- **Requirement**: With `_H` suffix, the base name must be ≤ 4 characters
- **Current examples**: `CH4_H` (5 chars, fits), `THF_H` (5 chars, fits)
- **Problem**: `ETOH_H` = 6 chars — **EXCEEDS LIMIT**
- **Solution**: Base name must be truncated/abbreviated. E.g.:
  - `ETOH` → `ETH_H` (5 chars, fits)
  - `METH` → `METH` + `_H` = 5 chars (fits)
  - `PROPANOL` → must be abbreviated to ≤ 4 chars → `PROP_H` (5 chars)
- **Implementation**: 
  1. User provides a desired molecule name
  2. Validate: `len(name + "_H") <= 5`
  3. If too long, either auto-truncate or ask user for a shorter name
  4. The truncated/abbreviated name must be used consistently in `.gro`, `.top`, and `.itp`

**Confidence: HIGH** — GROMACS format specification; enforced in existing code (e.g., `res_name[:5]` truncation in `write_ion_gro_file()` line 1655)

#### 2e. Residue name in `[ atoms ]` must match moleculetype name

- **Requirement**: Column 4 (resname) in every `[ atoms ]` line must match the `[moleculetype]` name
- **Example from ch4_hydrate.itp**:
  ```
  [ moleculetype ]
  CH4_H  3
  
  [ atoms ]
       1     c3         1      CH4_H    C              1   -0.46580968   12.010736
  ```
- **For custom guests**: After renaming `[moleculetype]` to `ETH_H`, ALL resname entries in `[ atoms ]` must also change to `ETH_H`

**Confidence: HIGH** — GROMACS requirement; verified in all bundled ITPs

#### 2f. Atom types must be GAFF2-compatible

- **Requirement**: All atom type names in the `[ atoms ]` section (column 2) must have corresponding entries in the `[ atomtypes ]` section of the main `.top` file
- **Common GAFF2 types**: `c3`, `c5`, `hc`, `h1`, `os`, `oh`, `ho`, `c_2`, `o_2`, `hn`, `na`, `cl`
- **For custom molecules**: The user's ITP may introduce atom types not in the current hardcoded set. These must be:
  1. Extracted from the ITP's `[atomtypes]` section (before commenting it out)
  2. Merged into the main `.top` file's `[atomtypes]` section
  3. Deduplicated against already-present types

**Confidence: HIGH** — Pattern already implemented in `write_ion_top_file()` and `write_custom_molecule_top_file()` for custom molecules

#### 2g. ITP must contain required topology sections

- **Minimum required**: `[ moleculetype ]` and `[ atoms ]`
- **Common additional sections**: `[ bonds ]`, `[ angles ]`, `[ dihedrals ]`, `[ pairs ]`, `[ exclusions ]`
- **Validation**: Check that at least `[ moleculetype ]` and `[ atoms ]` exist. Warn if `[ bonds ]` is missing (free molecule, may be acceptable for united-atom models but unusual for all-atom)

**Confidence: HIGH** — GROMACS topology format specification

### Summary Validation Checklist

| # | Check | Action on Failure | Severity |
|---|-------|-------------------|----------|
| 1 | `[moleculetype]` exists | REJECT — fatal | CRITICAL |
| 2 | `[atoms]` exists | REJECT — fatal | CRITICAL |
| 3 | Base name + "_H" ≤ 5 chars | REJECT with message asking for shorter name | CRITICAL |
| 4 | `[atomtypes]` uses sigma/epsilon (not A/B) | REJECT with explanation | CRITICAL |
| 5 | `[atomtypes]` commented out or absent | Auto-fix via `comment_out_atomtypes_in_itp()` | MODERATE |
| 6 | Residue name matches moleculetype | Auto-fix during name rewriting | MODERATE |
| 7 | All atom types have parameters in `[atomtypes]` | WARN — may cause GROMACS error at runtime | MODERATE |
| 8 | `[bonds]` exists | WARN — free molecule | LOW |

---

## 3. Atomtypes Merging Strategy for .top Files

### Current approach (hardcoded)

The existing code uses **hardcoded GAFF2 atomtype definitions** for known guests:

```python
# From write_interface_top_file() lines 1046-1072:
if guest_type == "ch4":
    f.write("c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
    f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
elif guest_type == "thf":
    f.write("os        os        8             15.9994  0.0     A      3.15610e-1    3.03758e-1\n")
    f.write("c5        c5        6             12.0107  0.0     A      3.39771e-1    4.51035e-1\n")
    f.write("hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2\n")
    f.write("h1        h1        1              1.0079  0.0     A      2.42200e-1    8.70272e-2\n")
```

For custom molecules, the code **parses atomtypes from the user's ITP** with deduplication:

```python
# From write_ion_top_file() lines 1874-1884:
_written_atomtypes = {"OW_ice", "HW_ice", "MW", ...}  # Already written
if has_custom and ion_structure.custom_itp_path:
    custom_atomtypes = parse_itp_atomtypes(custom_itp_path)
    if custom_atomtypes:
        for atomtype in custom_atomtypes:
            if len(atomtype) >= 8 and atomtype[0] not in _written_atomtypes:
                f.write(f"{atomtype[0]:<8s} {atomtype[1]:<8s} ...")
                _written_atomtypes.add(atomtype[0])
```

**Confidence: HIGH** — Directly from source code

### Recommended strategy for custom hydrate guests

For custom hydrate guests, we need a hybrid approach that combines the existing patterns:

#### Step 1: Extract atomtypes from user's ITP before commenting them out

```python
# Parse atomtypes from user's original ITP (before modification)
custom_atomtypes = parse_itp_atomtypes(user_itp_path)
```

The `parse_itp_atomtypes()` function (lines 265-313) already handles both 7-column and 8-column formats, normalizing to 8 columns by inserting a bond_type.

#### Step 2: Build the `[atomtypes]` section with deduplication

Maintain a `_written_atomtypes` set (already established pattern). Write:
1. TIP4P-ICE water atomtypes (always: OW_ice, HW_ice, MW)
2. Ion atomtypes if present (NA, CL)
3. Hardcoded GAFF2 atomtypes for known built-in guests (c3, hc, os, c5, h1, etc.)
4. **Custom guest atomtypes** parsed from user's ITP, skipping duplicates

**Deduplication rule**: If the atomtype name already exists in `_written_atomtypes`, skip it. This handles the common case where a custom molecule shares GAFF2 types with built-in guests (e.g., `hc`, `c3` shared between CH4 and ethanol).

**Important nuance**: For duplicate atomtypes with **identical parameters**, skipping is correct. For duplicates with **different parameters** (same name, different sigma/epsilon), this indicates a force field conflict — should WARN the user.

#### Step 3: Validate extracted atomtypes for comb-rule=2 compatibility

Before writing atomtypes, validate that all values are in sigma/epsilon format:

```python
def validate_atomtypes_comb_rule_2(atomtypes: list[tuple]) -> list[str]:
    """Validate atomtypes are compatible with comb-rule=2 (sigma/epsilon format).
    
    Returns list of error messages (empty if valid).
    """
    errors = []
    for at in atomtypes:
        if len(at) >= 8:
            try:
                sigma = float(at[6])  # Column 7 (0-indexed: 6) is sigma
                # sigma in nm for organic atoms is typically 0.1-0.5
                # A/B format C6 values are typically >> 100
                if sigma > 10:
                    errors.append(
                        f"Atomtype '{at[0]}': sigma value {sigma} is too large for nm units. "
                        f"This likely indicates A/B format (C6/C12) which is incompatible "
                        f"with comb-rule=2 (Lorentz-Berthelot). "
                        f"Use sigma/epsilon format instead."
                    )
            except (ValueError, IndexError):
                pass
    return errors
```

#### Step 4: Write atomtypes to .top, then comment out in ITP

1. Write all atomtypes to the main `.top` file's `[atomtypes]` section
2. Apply `comment_out_atomtypes_in_itp()` to the user's ITP before including it via `#include`

**Confidence: HIGH** — All building blocks exist in the codebase; the strategy extends established patterns

### Handling GAFF2 atom type overlaps

The key overlap concern: custom molecules often share GAFF2 types with built-in guests. For example, ethanol uses `c3`, `hc`, `h1` — all of which overlap with CH4 and THF.

**Current dedup approach** (from `_written_atomtypes` set) is correct for identical parameters. The hardcoded GAFF2 values in the `.top` writer and the values in `etoh.itp`'s `[atomtypes]` are **identical** (same GAFF2 force field), so skipping duplicates is safe.

**Verification**: Compare values between `ch4.itp` and `etoh.itp`:
- `c3`: ch4.itp has `3.397710E-01 / 4.510352E-01`; etoh.itp has `3.397710E-01 / 4.510352E-01` — **IDENTICAL** ✓
- `hc`: ch4.itp has `2.600177E-01 / 8.702720E-02`; etoh.itp has `2.600177E-01 / 8.702720E-02` — **IDENTICAL** ✓
- `h1`: etoh.itp has `2.421997E-01 / 8.702720E-02`; thf.itp has `2.421997E-01 / 8.702720E-02` — **IDENTICAL** ✓

**Confidence: HIGH** — All values verified from source files

### What about non-GAFF2 atom types?

If a user provides an ITP with non-GAFF2 atom types (e.g., OPLS-AA, CHARMM), the atomtypes will still be parsed and written to the `.top` file. However, this creates a **force field mixing problem**:

- TIP4P-ICE water parameters are specific to the water model
- GAFF2 guest parameters are calibrated with TIP4P-ICE cross-interactions using comb-rule=2
- Non-GAFF2 atom types may have different combining rules or cross-interaction behavior

**Recommendation**: 
- Allow non-GAFF2 atom types but **WARN** the user
- Document that GAFF2 + TIP4P-ICE with comb-rule=2 is the tested configuration
- Non-GAFF2 force fields may require custom cross-interaction parameters via `[ nonbond_params ]`

**Confidence: MEDIUM** — Force field mixing is a well-known issue in MD, but the specific impact depends on the user's system

---

## 4. GRO Residue Name Length Constraints and Handling

### The 5-character limit

GROMACS `.gro` format specification: residue name field is **5 characters wide** (right-justified in a `%5s` format, or left-justified in `%5s` with leading space). In practice:

- GROMACS **strictly** limits residue names to 5 characters in `.gro` files
- Exceeding 5 characters causes GROMACS to truncate or misread the file
- The current code uses `{guest_res_name:<5s}` (left-justified, 5 chars wide)

### Impact on hydrate guest naming

With `_H` suffix (2 chars), the base name has at most **3 characters** for 5-char total:

| Base name | Hydrate name | Length | Status |
|-----------|-------------|--------|--------|
| CH4 | CH4_H | 5 | ✅ FITS |
| THF | THF_H | 5 | ✅ FITS |
| CO2 | CO2_H | 5 | ✅ FITS |
| H2 | H2_H | 4 | ✅ FITS |
| ETOH | ETOH_H | 6 | ❌ TOO LONG |
| ETH | ETH_H | 5 | ✅ FITS (abbreviated) |
| MEOH | MEOH_H | 6 | ❌ TOO LONG |
| MEO | MEO_H | 5 | ✅ FITS (abbreviated) |
| PROPANOL | PROPANOL_H | 9 | ❌ WAY TOO LONG |
| PROP | PROP_H | 5 | ✅ FITS (abbreviated) |

### Handling strategy

1. **User provides molecule name** → Validate length constraint
2. **If `len(name + "_H") > 5`** → Require user to provide an abbreviated name ≤ 3 chars
3. **Auto-suggestion**: Offer common abbreviations (ETOH→ETH, MEOH→MEO, PROPANOL→PRP, etc.)
4. **Hard limit**: Never write a residue name > 5 chars to `.gro` file

**Alternative approach** (not recommended): Use `_H` as implicit suffix and just truncate the base name to 3 chars. But this is fragile — "ETOH" truncated to 3 chars becomes "ETO", which is confusing.

**Recommended approach**: 
- Accept the user's desired molecule name
- If `len(name + "_H") <= 5`: Use it directly
- If `len(name + "_H") > 5`: **Reject with clear error**, suggest max 3-char base name
- The user must choose the base name at input time, not at export time

**Confidence: HIGH** — GROMACS format specification; existing code pattern

### Consistency across files

The moleculetype name must be **identical** across all three locations:
1. `.gro` file: residue name column (5 chars max)
2. `.top` file: `[molecules]` section molecule name
3. `.itp` file: `[moleculetype]` section name + `[atoms]` resname column

All three must use the same `_H`-suffixed name (e.g., `ETH_H`).

**Confidence: HIGH** — GROMACS requirement; verified pattern in existing ITP files

---

## 5. comb-rule=2 Compatibility Validation Approach

### What comb-rule=2 means

With `comb-rule=2` (Lorentz-Berthelot combining rules):
- **sigma_ij = (sigma_i + sigma_j) / 2** (arithmetic mean)
- **epsilon_ij = sqrt(epsilon_i × epsilon_j)** (geometric mean)

This is the AMBER/GAFF2 convention. The alternative, `comb-rule=1`, uses:
- **sigma_ij = (sigma_i + sigma_j) / 2** (same)
- **epsilon_ij = sqrt(epsilon_i × epsilon_j)** (same)
- But for A/B format: **A_ij = sqrt(A_i × A_j)** and **B_ij = sqrt(B_i × B_j)**

The critical difference: In A/B format, the LJ potential is written as:
```
V(r) = A/r^12 - B/r^6
```
Instead of the standard sigma/epsilon form:
```
V(r) = 4ε[(σ/r)^12 - (σ/r)^6]
```

These are mathematically equivalent with:
- A = 4εσ^12
- B = 4εσ^6

But combining rules for A/B are **different** from sigma/epsilon under comb-rule=2.

### Detection algorithm

```python
def detect_atomtypes_format(atomtypes: list[tuple[str, ...]]) -> str:
    """Detect whether atomtypes section uses sigma/epsilon or A/B format.
    
    Returns:
        'sigma_epsilon' or 'ab_format' or 'unknown'
    
    Heuristic:
        - sigma/epsilon: column 7 values are ~0.1-0.5 (nm), column 8 values are ~0.001-1.0 (kJ/mol)
        - A/B: column 7 values are >>1 (A = 4εσ^12, typically 10^6+), column 8 values are >>1 (B = 4εσ^6, typically 10^2+)
    """
    if not atomtypes:
        return 'unknown'
    
    for at in atomtypes:
        if len(at) < 8:
            continue
        try:
            val7 = float(at[6])  # sigma or A
            if val7 > 10:
                return 'ab_format'  # sigma in nm is never > 10
        except (ValueError, IndexError):
            continue
    
    return 'sigma_epsilon'
```

### Validation flow

```
User provides ITP file
    ↓
Parse [atomtypes] section → parse_itp_atomtypes()
    ↓
Detect format → detect_atomtypes_format()
    ↓
If 'ab_format':
    REJECT with error: "ITP uses A/B LJ format (comb-rule=1), 
    but QuickIce requires sigma/epsilon format (comb-rule=2). 
    Convert using: sigma = (A/B)^(1/6), epsilon = B^2/(4A)"
    ↓
If 'sigma_epsilon':
    Continue → extract atomtypes, merge into .top
    ↓
If 'unknown' (no [atomtypes] section):
    Check if atom types in [atoms] are known GAFF2 types
    If all known → OK, use hardcoded values
    If unknown types → WARN: "Unknown atom types without [atomtypes] 
    definition; GROMACS will error at runtime"
```

### A/B → sigma/epsilon conversion (for user guidance)

If we want to offer auto-conversion:

```
sigma = (A/B)^(1/6)
epsilon = B^2 / (4*A)
```

Or equivalently:
```
sigma = (A / B)^(1/6)
epsilon = B^2 / (4 * A)
```

However, **auto-conversion is risky** — rounding errors and unit mismatches could produce subtly wrong parameters. Better to REJECT and ask the user to regenerate the ITP with sigma/epsilon format using Sobtop or ACPYPE with the correct comb-rule setting.

**Confidence: HIGH** — GROMACS documentation; mathematical relationship verified

---

## 6. Example: Converting etoh.itp to Hydrate Guest Format (ETH_H)

### Source file: `quickice/data/custom/etoh.itp`

The existing ethanol ITP has:
- `[atomtypes]` section: **ACTIVE** (not commented out) with 5 atom types (hc, c3, h1, oh, ho)
- `[moleculetype]` name: `etoh`
- `[atoms]` resname: `MOL` (generic, not matching moleculetype!)
- 9 atoms: H, C, H, H, C, H, H, O, H

### Required transformations

To create a hydrate guest ITP (`eth_h.itp`), apply these transformations:

#### Step 1: Comment out `[atomtypes]` section

Apply `comment_out_atomtypes_in_itp()`:

**Before:**
```
[ atomtypes ]
; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)
hc           1     1.007941    0.000000    A      2.600177E-01    8.702720E-02
c3           6    12.010736    0.000000    A      3.397710E-01    4.510352E-01
h1           1     1.007941    0.000000    A      2.421997E-01    8.702720E-02
oh           8    15.999405    0.000000    A      3.242871E-01    3.891120E-01
ho           1     1.007941    0.000000    A      5.379246E-02    1.966480E-02
```

**After:**
```
; Modified for QuickIce: [atomtypes] commented - types defined in main .top file
; [ atomtypes ]
; name   at.num      mass       charge   ptype     sigma (nm)    epsilon (kJ/mol)
; hc           1     1.007941    0.000000    A      2.600177E-01    8.702720E-02
; c3           6    12.010736    0.000000    A      3.397710E-01    4.510352E-01
; h1           1     1.007941    0.000000    A      2.421997E-01    8.702720E-02
; oh           8    15.999405    0.000000    A      3.242871E-01    3.891120E-01
; ho           1     1.007941    0.000000    A      5.379246E-02    1.966480E-02
```

#### Step 2: Rename `[moleculetype]` to `ETH_H`

**Before:**
```
[ moleculetype ]
; name          nrexcl
etoh       3
```

**After:**
```
[ moleculetype ]
; name          nrexcl
ETH_H  3
```

Note: `ETH_H` is exactly 5 characters — fits GRO format limit. The base name `ETH` is 3 chars + `_H` (2 chars) = 5 chars.

#### Step 3: Rename residue name in `[atoms]` from `MOL` to `ETH_H`

**Before:**
```
[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     hc         1      MOL     H              1    0.05772791    1.007941
     2     c3         1      MOL     C              2   -0.21810187   12.010736
     ...
```

**After:**
```
[ atoms ]
;  Index   type   residue  resname   atom         cgnr     charge       mass
     1     hc         1      ETH_H    H              1    0.05772791    1.007941
     2     c3         1      ETH_H    C              2   -0.21810187   12.010736
     ...
```

#### Step 4: Extract atomtypes for .top file

The 5 atom types from etoh.itp that need to be in the main `.top`:

| Type | Atomic# | Mass | sigma (nm) | epsilon (kJ/mol) | Notes |
|------|---------|------|-----------|-------------------|-------|
| hc | 1 | 1.0079 | 0.26002 | 0.08703 | Shared with CH4/THF — **DEDUP** |
| c3 | 6 | 12.0107 | 0.33977 | 0.45104 | Shared with CH4 — **DEDUP** |
| h1 | 1 | 1.0079 | 0.24220 | 0.08703 | Shared with THF — **DEDUP** |
| oh | 8 | 15.9994 | 0.32429 | 0.38911 | **NEW** — must write |
| ho | 1 | 1.0079 | 0.05379 | 0.01966 | **NEW** — must write |

So in a system with CH4 hydrate guests + ETH_H hydrate guests, the `[atomtypes]` section would contain:

```
[ atomtypes ]
; name   bond_type  atomic_number  mass     charge  ptype  sigma (nm)    epsilon (kJ/mol)
OW_ice   OW_ice    8             15.9994  0.0     A      3.16680e-1    8.82110e-1
HW_ice   HW_ice    1              1.0080  0.0     A      0.0           0.0
MW       MW        0              0.0000  0.0     V      0.0           0.0
; CH4 atom types (GAFF2)
c3        c3        6             12.0107  0.0     A      3.39771e-1    4.51035e-1
hc        hc        1              1.0079  0.0     A      2.60018e-1    8.70272e-2
; ETH_H custom hydrate guest atom types (GAFF2)
oh        oh        8             15.9994  0.0     A      3.24287e-1    3.89112e-1
ho        ho        1              1.0079  0.0     A      5.37925e-2    1.96648e-2
```

Note: `hc`, `c3`, `h1` are deduplicated (already written for CH4/THF). Only `oh` and `ho` are new.

#### Step 5: Resulting .top `[molecules]` section

```
[ molecules ]
; Compound        #mols
SOL              {sol_count}
CH4_H            {ch4_guest_count}
ETH_H            {eth_guest_count}
```

#### Step 6: Resulting .gro residue names

```
    1SOL     OW    1   0.123   0.456   0.789     ; Water
  100CH4_H    C  100   1.234   5.678   9.012     ; CH4 guest
  101ETH_H    H  101   2.345   6.789   0.123     ; Ethanol guest (resname = ETH_H, 5 chars)
```

**Confidence: HIGH** — All transformations follow established patterns in the codebase

---

## 7. Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| Current pipeline architecture | HIGH | All code read and verified directly |
| ITP validation requirements | HIGH | Based on GROMACS spec + existing code patterns |
| Atomtypes merging strategy | HIGH | Existing dedup pattern in `write_ion_top_file()` / `write_custom_molecule_top_file()` |
| GRO residue name constraint | HIGH | GROMACS format specification, verified in code |
| comb-rule=2 detection | HIGH | Mathematical relationship well-established |
| etoh.itp conversion example | HIGH | All data from source files |
| Force field mixing warnings | MEDIUM | General MD knowledge, but specific cross-interaction effects depend on user's system |
| GAFF2 atomtype overlap safety | HIGH | Verified identical values across all bundled ITPs |

---

## 8. Blockers and Open Questions

### Blockers

**No critical blockers identified.** All building blocks exist in the codebase:
- `comment_out_atomtypes_in_itp()` — handles ITP atomtype commenting
- `parse_itp_atomtypes()` — extracts atomtype definitions from ITP
- `parse_itp_file()` — extracts moleculetype name, atom names, atom types
- `_written_atomtypes` dedup pattern — handles atomtype merging
- `MoleculetypeRegistry.register_hydrate_guest()` — handles `_H` suffix naming
- `get_hydrate_guest_residue_name()` — reads residue name from hydrate ITP

### Open questions for implementation

1. **Custom guest ITP file generation**: Should QuickIce generate the `_hydrate.itp` variant at export time (transform user's original ITP), or should the user be required to provide a pre-formatted hydrate ITP?
   - **Recommendation**: Generate at export time. Apply: (1) comment out atomtypes, (2) rename moleculetype, (3) rename residue names. This matches the pattern used for built-in guests (ch4.itp → ch4_hydrate.itp is a pre-made variant, but for custom guests we should automate this).

2. **Custom guest name input**: Where in the GUI/CLI does the user specify the custom guest molecule name? The current custom molecule path (Tab 3) uses `register_custom_molecule()`, which doesn't add `_H` suffix. We need a separate code path for "custom hydrate guest" vs "custom liquid molecule".
   - **Recommendation**: Add a `register_custom_hydrate_guest()` method to `MoleculetypeRegistry` that applies the `_H` suffix and validates the 5-char limit.

3. **Atom reordering for custom guests**: Built-in guests CH4 and THF need atom reordering to match ITP canonical order (GenIce2 outputs atoms in different order). For custom guests, the user's GRO file provides atoms in the same order as their ITP — no reordering needed. But this should be **verified** at runtime.
   - **Recommendation**: For custom guests, use atom names as-is from the user's GRO file. The ITP `[atoms]` section already defines the canonical order, and the user's GRO should match it.

4. **GRO file format for custom guests**: The user provides a `.gro` file with their custom molecule. Currently `etoh.gro` uses residue name `MOL`. When this molecule is placed in hydrate cages, the `.gro` export must use the `_H`-suffixed residue name.
   - **Recommendation**: At export time, rewrite residue names in the GRO output to match the hydrate moleculetype name (e.g., `MOL` → `ETH_H`).

5. **What if the same custom molecule appears as both hydrate guest AND liquid solute?** This would require two separate ITP variants: `ETH_H` (hydrate) and `ETH_L` (liquid). Currently the registry supports both via `register_hydrate_guest()` and `register_liquid_solute()`.
   - **Recommendation**: Generate both variants at export time if needed. The base ITP transformation is the same; only the suffix changes.

---

## Appendix A: Key Functions Reference

| Function | Location | Purpose |
|----------|----------|---------|
| `parse_itp_file()` | `itp_parser.py:34` | Parse moleculetype name, atom count, atom types/names |
| `parse_itp_atomtypes()` | `gromacs_writer.py:265` | Extract atomtype definitions from ITP `[atomtypes]` section |
| `comment_out_atomtypes_in_itp()` | `gromacs_writer.py:316` | Comment out `[atomtypes]` section in ITP content |
| `parse_itp_residue_name()` | `gromacs_writer.py:222` | Read residue name from ITP `[atoms]` section |
| `get_hydrate_guest_residue_name()` | `gromacs_writer.py:399` | Get `_H`-suffixed residue name for hydrate guest |
| `detect_guest_type_from_atoms()` | `gromacs_writer.py:947` | Auto-detect guest type from atom names |
| `reorder_guest_atoms()` | `gromacs_writer.py:155` | Reorder atoms to match ITP canonical order |
| `MoleculetypeRegistry.register_hydrate_guest()` | `moleculetype_registry.py:46` | Register hydrate guest with `_H` suffix |
| `MoleculetypeRegistry.register_liquid_solute()` | `moleculetype_registry.py:71` | Register liquid solute with `_L` suffix |
| `MoleculetypeRegistry.register_custom_molecule()` | `moleculetype_registry.py:96` | Register custom molecule (no suffix) |

## Appendix B: Bundled ITP Files Summary

| File | Moleculetype | Resname | Atoms | Atomtypes | Has `[atomtypes]` |
|------|-------------|---------|-------|-----------|-------------------|
| `ch4.itp` | `ch4` | `CH4` | 5 | c3, hc | Commented out |
| `ch4_hydrate.itp` | `CH4_H` | `CH4_H` | 5 | c3, hc | Commented out |
| `ch4_liquid.itp` | `CH4_L` | `CH4_L` | 5 | c3, hc | Commented out |
| `thf.itp` | `thf` | `THF` | 13 | os, c5, hc, h1 | Commented out |
| `thf_hydrate.itp` | `THF_H` | `THF_H` | 13 | os, c5, hc, h1 | Commented out |
| `thf_liquid.itp` | `THF_L` | `THF_L` | 13 | os, c5, hc, h1 | Commented out |
| `tip4p-ice.itp` | `SOL` | `SOL` | 4 | OW_ice, HW_ice, MW | Commented out |
| `custom/etoh.itp` | `etoh` | `MOL` | 9 | hc, c3, h1, oh, ho | **ACTIVE** (not commented) |

## Appendix C: GAFF2 Atom Type Reference (from bundled ITPs)

| Type | Element | sigma (nm) | epsilon (kJ/mol) | Used by |
|------|---------|-----------|-------------------|---------|
| OW_ice | O | 3.16680e-1 | 8.82110e-1 | TIP4P-ICE water |
| HW_ice | H | 0.0 | 0.0 | TIP4P-ICE water |
| MW | (virtual) | 0.0 | 0.0 | TIP4P-ICE water |
| c3 | C | 3.39771e-1 | 4.51035e-1 | CH4, EtOH (sp3 carbon) |
| hc | H | 2.60018e-1 | 8.70272e-2 | CH4, EtOH, THF (carbon H) |
| c5 | C | 3.39771e-1 | 4.51035e-1 | THF (ring carbon) |
| os | O | 3.15610e-1 | 3.03758e-1 | THF (ether O) |
| h1 | H | 2.42200e-1 | 8.70272e-2 | THF, EtOH (alpha H) |
| oh | O | 3.24287e-1 | 3.89112e-1 | EtOH (hydroxyl O) |
| ho | H | 5.37925e-2 | 1.96648e-2 | EtOH (hydroxyl H) |
| c_2 | C | 3.39955e-1 | 4.39089e-1 | CO2 |
| o_2 | O | 3.02714e-1 | 8.80314e-1 | CO2 |
| hn | H | 0.0 | 0.0 | H2 |
| NA | Na | 2.21737e-1 | 1.47236e0 | Na+ (Madrid2019) |
| CL | Cl | 4.69906e-1 | 7.69231e-2 | Cl- (Madrid2019) |
