# Research Plan: Custom Guest Molecule in Hydrate

**Created:** 2026-06-22
**Status:** Draft — awaiting approval
**Target milestone:** Post-v5.5 (likely v6.5 or v7.0)
**Confidence in scope:** MEDIUM — core API verified, integration details need testing

---

## Problem Statement

QuickIce generates clathrate hydrate structures (sI, sII, sH) using GenIce2, which natively supports a fixed set of guest molecules (CH4, THF, CO2, H2, etc.) via Python plugins. Users want to place **arbitrary custom guest molecules** (ethanol, propane, cyclopentane, etc.) into hydrate cages, providing their own `.gro` + `.itp` file pairs — the same input mechanism already used by `CustomMoleculeInserter` for liquid-phase molecules.

The core question: **How do we bridge user-provided molecular data with GenIce2's internal cage-guest insertion pipeline?**

---

## Three Candidate Approaches

### Approach A: GenIce2 `mol` Plugin (Runtime Registration)

**Idea:** Use GenIce2's existing `mol[filename.mol]` molecule plugin, which reads MolView-format `.mol` files and creates a `Molecule` subclass instance at runtime. GenIce2 then handles cage center placement, random rotation, and GRO output automatically.

**What we verified:**

- GenIce2's `safe_import("molecule", guest_type)` loads molecule plugins by name
- `plugin_option_parser("mol[ethanol.mol]")` → `guest_type="mol"`, `guest_options={"ethanol.mol": True}`
- `audit_name("mol")` passes (alphanumeric check on plugin name, not options)
- `mol.Molecule(**guest_options)` reads the `.mol` file, sets `sites_`, `labels_`, `name_`
- GenIce2 Stage7 then does: `gmol = safe_import("molecule", guest_type).Molecule(**guest_options)`, followed by `arrange(cage_center, self.repcell, cmat, gmol)` to place at cage centers

**Mapping user input to GenIce2's Molecule class:**

| GenIce2 Molecule attr | Source | How to get |
|------------------------|--------|------------|
| `sites_` (3D coords, nm) | User's `.gro` file | Parse GRO, center at origin, convert Å→nm |
| `labels_` (atom names) | User's `.gro` or `.itp` | ITP `[atoms]` section column 5 (atom name) |
| `name_` (residue name) | User's `.itp` file | ITP `[moleculetype]` section name, append `_H` |

**Key issue:** The `mol` plugin reads MolView format (not GRO). We'd need to either:
1. Convert user's `.gro` → `.mol` on the fly before calling GenIce2, OR
2. Create a **new molecule plugin** (`custom`) that reads `.gro` files directly

**Pros:**
- GenIce2 handles ALL cage placement logic (center positions, random rotation, cage occupancy assignment)
- No need to extract cage positions ourselves
- GRO output already correct
- Minimal new code — just a `.mol` converter or a custom plugin

**Cons:**
- Couples us to GenIce2's internal behavior (any GenIce2 update could break this)
- GenIce2 uses random rotation for guests (no user control over orientation)
- `.mol` format conversion adds complexity and a failure mode
- Guest molecule residue name in GRO output comes from `name_` (must match ITP `_H` convention)
- GenIce2 does NOT validate guest-cage size fit — user silently gets a bad structure if guest is too large

### Approach B: Bypass GenIce2 Guest Insertion (Post-Processing)

**Idea:** Generate the empty hydrate water framework with GenIce2 (no guests), then extract cage center positions and use QuickIce's own insertion logic to place custom guest molecules at cage centers.

**What we verified:**

- GenIce2 lattice modules expose `cagepos` (fractional coords) and `cagetype` (cage ID strings) attributes
- `HydrateStructureGenerator._run_via_api()` can call GenIce2 with `guests={}` (empty dict) to get a water-only framework
- GenIce2's `GenIce` object stores `repcagepos` and `repcagetype` after `Stage1` — these are the replicated cage center positions in fractional coordinates
- Current code DISCARDS GenIce2's cage info after `generate_ice()` returns a GRO string
- We'd need to either: (1) intercept GenIce2 internal state before GRO serialization, or (2) use the lattice module's `cagepos`/`cagetype` directly and replicate ourselves

**Pros:**
- Full control over guest placement (custom rotation, orientation, validation)
- Can add cage-guest size validation
- Decoupled from GenIce2 internals — more robust to GenIce2 updates
- Reuses existing `CustomMoleculeInserter` patterns (cKDTree overlap checking, template placement)

**Cons:**
- Need to extract/calculate cage center positions ourselves (GenIce2 does this in Stage1 but doesn't expose it in output)
- Need to replicate cage positions for supercell (GenIce2 does this internally with `reshape_matrix`)
- Need to handle cage occupancy assignment (which cages get filled, random selection at given occupancy)
- More new code — essentially reimplementing parts of GenIce2's Stage7
- GRO output formatting must handle guest residue names, sequence numbers, etc.

### Approach C: Hybrid — GenIce2 for Positions, QuickIce for Guests

**Idea:** Run GenIce2 with a known small guest (e.g., CH4), extract the cage center positions from the output, then post-process to replace CH4 atoms with custom guest coordinates at those positions.

**What we verified:**

- GenIce2's GRO output includes guest atoms with residue names and positions
- After `generate_ice()`, we parse GRO and already identify guest molecules in `_build_molecule_index()`
- We could detect all CH4 positions, then replace each CH4 with the custom guest centered at the same position
- This is a "swap" operation: remove old guest atoms, insert new guest atoms at same centers

**Pros:**
- Gets cage positions "for free" from GenIce2's GRO output (no internal API hacking)
- No need to replicate cage positions manually
- GenIce2 handles occupancy assignment

**Cons:**
- Fragile — depends on correct identification of placeholder guest atoms in GRO output
- CH4 has 5 atoms (or 1 for united-atom Me), custom guest has N atoms — atom count changes, residue sequence numbers shift
- GRO line count, residue numbering, atom naming all need reworking
- Must handle different cage types separately (small/large cages may have different occupancy)
- Essentially the same "post-processing insert" as Approach B, but with a wasteful generate-then-discard step

---

## Recommended Approach: **A (with fallback to B)**

**Approach A is the best starting point** because:

1. **GenIce2 already has the `mol` plugin** that reads external molecule files and creates `Molecule` instances at runtime — this is literally designed for custom guests
2. **The plugin_option_parser bracket syntax is verified** — `mol[file=path]` passes the filename as a keyword argument
3. **GenIce2 handles ALL the hard parts** — cage replication, center placement, random rotation, occupancy assignment, GRO formatting
4. **Minimal new code** — we need a `.gro` → `.mol` converter (or a custom `custom_molecule` plugin that reads GRO directly)
5. **The existing QuickIce infrastructure** (MoleculetypeRegistry `_H` suffix, ITP handling) plugs in naturally

**The specific implementation path:**

1. **Create a `custom_guest` molecule adapter class** (NOT a GenIce2 plugin) that takes user's GRO+ITP data and produces a `genice2.molecules.Molecule`-compatible object with correct `sites_`, `labels_`, `name_`
2. **Monkey-patch or wrap `safe_import`** so that when GenIce2 calls `safe_import("molecule", guest_type).Molecule(**guest_options)`, it returns our adapter instead of looking for a plugin
3. **After GenIce2 generates the GRO**, post-process the residue names to match the `_H` convention (e.g., `ETH_H` instead of whatever GenIce2's `name_` produced)
4. **For GROMACS export**, use the user-provided ITP file (with `_H` suffix moleculetype name) — same pattern as existing `ch4_hydrate.itp` and `thf_hydrate.itp`

**Fallback to B if:**
- GenIce2's `safe_import` proves too brittle to intercept
- GenIce2's internal placement produces incorrect results for multi-atom guests
- We need user control over guest orientation (GenIce2 uses random rotation)

**Why NOT C:** It's strictly worse than A (more complex, less reliable, same outcome). It's also worse than B (less control, same amount of post-processing).

---

## Research Questions & Agent Tasks

### Task R1: GenIce2 `safe_import` Interception Feasibility

**Priority:** CRITICAL — determines if Approach A works
**Dependencies:** None
**Estimated effort:** 15-20 min

**Questions to answer:**

1. Can we subclass or monkey-patch `genice2.plugin.safe_import` to return a custom module when the guest type is our custom molecule? Test with a small script that:
   - Creates a simple `Molecule` subclass (e.g., 3-atom ethanol model)
   - Patches `safe_import` to return it
   - Calls `GenIce(...).generate_ice(formatter, water, guests={"12": {"custom_guest": 1.0}})`
   - Checks if the GRO output contains the custom guest at cage centers

2. Alternative: Can we register a module in `sys.modules` under the name `genice2.molecules.custom_guest` so that `safe_import` finds it? This avoids monkey-patching.

3. Can we use the `mol[file=path]` syntax directly? Create a `.mol` file from user's GRO data, pass `mol[file=ethanol.mol]` as the guest spec. Test end-to-end.

4. What happens if `name_` (residue name) exceeds 5 characters in GRO format? GenIce2 uses fixed-width GRO columns — does it truncate or error?

**How to test:**

```python
# Test 1: sys.modules injection
import sys
import types
mod = types.ModuleType("genice2.molecules.custom_guest")
class Molecule(genice2.molecules.Molecule):
    def __init__(self, **kwargs):
        self.sites_ = np.array([...])  # 3-atom ethanol coords in nm
        self.labels_ = ["C1", "C2", "O"]
        self.name_ = "ETH"
mod.Molecule = Molecule
sys.modules["genice2.molecules.custom_guest"] = mod

# Then call GenIce with guests={"12": {"custom_guest": 1.0}}
```

**Deliverable:** Short report with working code snippet or documented failure mode.

---

### Task R2: GRO → GenIce2 Molecule Bridge

**Priority:** HIGH — needed for Approach A regardless of R1 outcome
**Dependencies:** R1 (need to know which injection method works)
**Estimated effort:** 20-30 min

**Questions to answer:**

1. How to convert user's `.gro` file (positions in nm, atom names) into GenIce2's `Molecule` format:
   - `sites_`: Positions relative to center of mass, in nm. GenIce2's `Molecule.get()` returns these as `intra` (intra-molecular displacements). The `arrange()` function does: `rotated = intra @ rotmatrices[order]`, then `abscom + rotated`. So `sites_` must be **centered at origin** (COM subtracted).
   - `labels_`: Atom names matching the ITP file's `[atoms]` section column 5
   - `name_`: Residue name — must match ITP moleculetype name with `_H` suffix

2. Does the `.gro` file provide enough information? Current `parse_gro_file()` returns `(positions, atom_names, cell)`. We need atom names that match the ITP, which they should since the user provides both files for the same molecule.

3. Centering: The user's `.gro` file has absolute positions. We need to subtract the center of mass to get relative positions for `sites_`. This is straightforward: `sites = positions - positions.mean(axis=0)`.

4. **GRO vs ITP atom name mismatch:** The GRO file uses "atom name" (column 11-15, max 5 chars). The ITP uses "atom name" (column 5 in `[atoms]` section). These should match but may differ in practice (e.g., GRO uses "C" but ITP uses "C1"). How to handle?

5. **The `.mol` format alternative:** If using the `mol` plugin path, we'd convert GRO → MOL format. The MOL format is simple (line 1 = name, line 4 = atom count, then x y z element per line). Worth testing as a simpler integration path.

**Deliverable:** Working conversion function + documented edge cases.

---

### Task R3: Cage Center Extraction for Approach B

**Priority:** MEDIUM — needed only if Approach A fails
**Dependencies:** None (independent of R1)
**Estimated effort:** 15-20 min

**Questions to answer:**

1. Can we call GenIce2 with `guests={}` and still get cage positions from the `GenIce` object? The cage positions are set in `Stage1` before guest insertion in `Stage7`. If we call `generate_ice(guests={})`, does `self.repcagepos` still get populated?

2. Alternative: Use lattice module's `cagepos`/`cagetype` directly and replicate for the supercell ourselves. The replication formula is in GenIce2's `Stage1`:
   ```python
   repcagepos = replicate_positions(cagepos1, replica_vectors, reshape_matrix)
   ```
   Can we import and use `replicate_positions` directly?

3. What about `assess_cages=True`? GenIce2 has a `cage.assess_cages()` method that detects cages from the water network topology. Is this more robust than relying on lattice-provided positions?

4. Cage diameters for validation. From the hydrate-analysis research:
   - 5¹² (small): ~3.9 Å radius → ~7.8 Å diameter
   - 5¹²6² (sI large): ~4.3 Å → ~8.6 Å
   - 5¹²6⁴ (sII large): ~4.7 Å → ~9.4 Å
   - 5¹²6⁸ (sH large): ~5.7 Å → ~11.4 Å
   
   How to compute the guest's effective diameter from its GRO coordinates? Options:
   - Maximum pairwise distance between atoms
   - Maximum distance from COM to any atom
   - Van der Waals radius envelope (requires element knowledge)

**Deliverable:** Working cage extraction code + diameter validation approach.

---

### Task R4: GROMACS Export for Custom Hydrate Guest

**Priority:** HIGH — needed regardless of approach
**Dependencies:** R2 (need to know how guest residue name is handled)
**Estimated effort:** 20-30 min

**Questions to answer:**

1. How does the current hydrate export pipeline handle guest ITP files? The pattern is:
   - `quickice/data/ch4_hydrate.itp` → `[moleculetype] CH4_H 3`
   - `quickice/data/thf_hydrate.itp` → `[moleculetype] THF_H 3`
   - In `.top`: `#include "ch4_hydrate.itp"`, then `[molecules] CH4_H N`
   - In `.gro`: residue name is `CH4_H` (5 chars max)

2. For custom guests, the user provides their own `.itp`. The required transformation:
   - Moleculetype name: user's name → `{name}_H` (e.g., `ETH_H`, `PRP_H`)
   - Residue name in `[atoms]` section: must match `{name}_H`
   - `[atomtypes]` section: must be commented out (defined in main `.top`)
   - `comb-rule=2` (Lorentz-Berthelot): All atomtypes must use sigma/epsilon format (NOT A/B format)

3. How to validate the user's ITP meets these constraints? The existing `parse_itp_file()` returns `ITPMoleculeInfo` with `molecule_name`, `atom_types`, `atom_names`, `has_atomtypes_section`. We need to check:
   - `has_atomtypes_section` → if True, warn user to remove it or auto-comment-out
   - Atom types must use sigma/epsilon format (check against known A/B format patterns)
   - Moleculetype name must be ≤ 5 chars (GRO residue name limit) including `_H` suffix → 4 chars max for the base name

4. The user's ITP defines `[atomtypes]` with LJ parameters. These need to go into the main `.top` file's `[atomtypes]` section alongside TIP4P-ICE and any other guest types. The existing `gromacs_writer.py` already handles this for CH4/THF (hardcoded c3, hc, os, c5, h1 types). For custom guests, we need to:
   - Extract atomtypes from user's ITP
   - Add them to the main `.top` `[atomtypes]` section
   - Handle duplicates (same type name from multiple guest ITPs)

5. **GRO residue name length:** GRO format allows 5-character residue names. With `_H` suffix, the base name can be at most 4 characters (e.g., `ETH_H`, `PRP_H`). What if the user's molecule name is longer? Truncate? Error?

**Deliverable:** Documented GROMACS export requirements + validation checklist for user-provided ITP files.

---

### Task R5: End-to-End Prototype

**Priority:** HIGH — validates the whole approach
**Dependencies:** R1, R2, R4
**Estimated effort:** 30-45 min

**Goal:** Build a minimal working prototype that places a custom guest (ethanol, 9 atoms) in sI hydrate small cages.

**Steps:**

1. Create a test `.gro` file for ethanol (9 atoms: C1, C2, O, H1-H6)
2. Create a test `.itp` file for ethanol (GAFF2 atom types: c3, oh, hc, ho)
3. Convert GRO → GenIce2 `Molecule` object (using R1/R2 findings)
4. Call GenIce2 with custom guest in `12` cages at 50% occupancy
5. Verify GRO output contains ethanol atoms at cage center positions
6. Verify the output can be parsed by `_build_molecule_index()` correctly
7. Test GROMACS export produces valid `.top` + `.gro` + `.itp`

**Success criteria:**
- GRO output shows ethanol residue at cage center positions
- `_build_molecule_index()` correctly identifies ethanol as guest (not "unknown")
- GROMACS `grompp` doesn't error on the exported topology (if gmx available)
- No overlap between ethanol atoms and water framework

**Deliverable:** Working prototype script + documented issues.

---

## Agent Task Dependency Graph

```
R1 (safe_import feasibility)  ──→  R2 (GRO→Molecule bridge)  ──→  R5 (E2E prototype)
                                                                      ↑
R3 (cage extraction - B path)         (independent fallback)          │
                                                                      │
R4 (GROMACS export)  ──────────────────────────────────────────────┘
```

**Wave 1:** R1, R3, R4 (all independent)
**Wave 2:** R2 (depends on R1)
**Wave 3:** R5 (depends on R1, R2, R4)

**Critical path:** R1 → R2 → R5

If R1 shows Approach A works → R2 and R5 follow the A path.
If R1 shows Approach A fails → R3 becomes critical, R2 pivots to B path, R5 uses B approach.

---

## What Each Agent Should Return

| Task | Format | Key Output |
|------|--------|------------|
| R1 | `.md` report + working code | Which injection method works (sys.modules, monkey-patch, mol plugin, or none) |
| R2 | `.md` report + conversion function | `gro_to_genice_molecule()` function with documented edge cases |
| R3 | `.md` report + extraction code | Cage center extraction function + diameter validation approach |
| R4 | `.md` report + validation checklist | ITP validation requirements + atomtypes handling strategy |
| R5 | `.md` report + prototype script | Working end-to-end demo or documented blockers |

---

## Known Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| GenIce2 `safe_import` can't be intercepted | Approach A fails → Approach B | R1 tests this first; R3 is independent backup |
| GRO residue name ≤ 5 chars (including `_H`) | User can't use long molecule names | Auto-truncate or require ≤4-char base names |
| GenIce2 random rotation may cause guest-cage overlap | Invalid structure for large guests | Add post-hoc validation (check all atoms within cage boundary) |
| User ITP has `[atomtypes]` with A/B format (not sigma/epsilon) | comb-rule=2 mismatch | Auto-detect and reject/warn; document required format |
| Multi-atom guest in small 5¹² cage | Guest too large for cage | Diameter validation (R3); warn user if guest > cage |

---

## Open Questions for User

1. **Should we support custom orientation for hydrate guests?** GenIce2 places guests with random rotation. For liquid-phase custom molecules, users can specify Euler angles. Do hydrate cage guests need the same control, or is random rotation acceptable?

2. **Cage-guest size validation policy:** Should QuickIce refuse to place a guest that's too large for the cage (hard block), or just warn and let the user proceed?

3. **`.mol` format support:** Should we support both `.gro`+`.itp` (current QuickIce pattern) AND `.mol` files (GenIce2 native format) as input for hydrate guests? Or only `.gro`+`.itp` for consistency?

4. **Mixed guests in different cage types:** Should we support different guest molecules in small vs large cages (e.g., CH4 in 5¹² + ethanol in 5¹²6²)? This is a binary clathrate — GenIce2's `parse_guest` already supports it syntax-wise.

---

## Approval Checkpoint

**Before spawning research agents, confirm:**

1. Approach A (GenIce2 plugin injection) is the preferred starting direction ☐
2. Approach B (bypass GenIce2) is the fallback if A fails ☐
3. Research should NOT install any new dependencies ☐
4. All work stored in `.planning/research/future-ml/custom-guest-hydrate/` ☐
5. User questions above can be deferred until after research completes ☐

**To approve:** Respond with "approved" or request modifications.
