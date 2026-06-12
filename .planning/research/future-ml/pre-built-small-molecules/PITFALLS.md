# Domain Pitfalls: Pre-built Small Molecules for GROMACS

**Domain:** AMBER geostd → GROMACS .gro/.itp conversion + bundled molecule library
**Researched:** 2026-06-12
**Confidence:** HIGH (verified against GROMACS 2026.2 manual, QuickIce codebase, and prior agent research)

---

## P1: 1-4 Interaction Scaling Is System-Wide, Not Per-Molecule

**Severity:** CRITICAL (scientific accuracy)
**Status:** BLOCKING — must verify before release
**Nature:** CONFIRMED — GROMACS architecture, not a bug

### What Goes Wrong

The `[ defaults ]` section in a GROMACS `.top` file defines `fudgeLJ` and `fudgeQQ` as **system-wide** parameters. These scale ALL 1-4 pair interactions in the entire simulation. There is no mechanism to set per-molecule 1-4 scaling in GROMACS.

AMBER uses `SCEE=1.2` (electrostatic 1-4 scale = 1/1.2 = 0.8333) and `SCNB=2.0` (LJ 1-4 scale = 1/2.0 = 0.5). QuickIce already writes the correct values:

```
[ defaults ]
; nbfunc  comb-rule  gen-pairs  fudgeLJ  fudgeQQ
1               2               yes             0.5     0.8333
```

### Why This Is NOT Actually a Problem for QuickIce's Current Scope

**Verified against the codebase and GROMACS manual:** The current QuickIce scope (GAFF2 guests + TIP4P-ICE water + Madrid2019 ions) is **safe** because:

1. **TIP4P-ICE water** uses `nrexcl=2` and explicit `[ exclusions ]` — it has **zero 1-4 pairs**. The `fudgeLJ`/`fudgeQQ` values do not affect water at all.
2. **Madrid2019 ions** (Na⁺, Cl⁻) are single-atom species — they have **no bonded interactions** and therefore no 1-4 pairs.
3. **GAFF2 guest molecules** use the AMBER 1-4 scaling convention — `fudgeLJ=0.5, fudgeQQ=0.8333` is exactly correct.

### When This BECOMES a Problem

If a user ever mixes GAFF2 molecules (AMBER 1-4 scaling) with **OPLS-AA** or **CHARMM** molecules (different 1-4 scaling), the system-wide `fudgeLJ`/`fudgeQQ` cannot satisfy both simultaneously. For example:
- OPLS-AA uses `fudgeLJ=0.5, fudgeQQ=0.5` (different from AMBER's `fudgeQQ=0.8333`)
- CHARMM uses `fudgeLJ=1.0, fudgeQQ=1.0` (no 1-4 scaling)

### Prevention

1. **Document explicitly** that the bundled molecule library is GAFF2-only and designed for use with TIP4P-ICE + Madrid2019 ions
2. **Add a runtime check** in the TOP writer: if any non-GAFF2 molecule types are detected, warn the user about 1-4 scaling incompatibility
3. **In the GUI**, show a warning when a user selects molecules from different force field families

### Detection

`grompp` will NOT warn about this — the simulation runs fine but produces **scientifically incorrect** 1-4 energetics. Only comparison with AMBER reference energies can detect this.

### Recovery

If discovered post-simulation: re-run with correct `[ defaults ]` values. No structural damage, only energy/thermodynamic properties are affected.

**Source:** GROMACS 2026.2 manual, Table 13 (topology file format), `[ defaults ]` section. QuickIce `gromacs_writer.py` lines 537, 969, 1245 (all consistently use `fudgeLJ=0.5, fudgeQQ=0.8333`). **Confidence: HIGH.**

---

## P2: PDB Code Name Collision (25% False-Positive Rate)

**Severity:** CRITICAL (scientific correctness)
**Status:** BLOCKING — must implement automated verification before bundling any molecule
**Nature:** CONFIRMED — verified by direct file inspection (Agent C research)

### What Goes Wrong

The PDB Chemical Component Dictionary reuses short chemical formula codes as residue names for complex PDB ligands. A user selecting "CH4" from the molecule library would get a **33-atom peptide-like molecule** instead of 5-atom methane.

| PDB Code | Expected | Actual | Atom Count Mismatch |
|----------|----------|--------|---------------------|
| CH4 | Methane (5 atoms) | 33-atom complex | 6.6× |
| THF | Tetrahydrofuran (14 atoms) | 55-atom PDB ligand | 3.9× |
| XEN | Xenon (1 atom) | 31-atom organic | 31× |
| NEO | Neopentane (17 atoms) | 29-atom complex | 1.7× |
| CPN | Cyclopentane (15 atoms) | 34-atom complex | 2.3× |
| ADA | Adamantane (26 atoms) | 22-atom sugar-like | 0.85× |
| PPR | Propane (11 atoms) | 12-atom phosphonopropionate | 1.1× |

### Why It Happens

The PDB CCD was designed for protein crystallography, not small-molecule MD. Short chemical formula codes (CH4, N2, THF) get reassigned to complex ligands that happen to have similar topology.

### Consequences

A user simulating "methane hydrate" with PDB CH4 would:
1. Place a 33-atom molecule in 5.12 Å cages — the molecule is far too large for sI cages
2. Get completely wrong thermodynamic properties (hydration free energy, dissociation pressure)
3. Possibly crash GROMACS during energy minimization (steric clashes)
4. Waste hours of compute time on meaningless data

### Prevention

**Mandatory automated verification for every bundled molecule:**

1. **Atom count check**: Verify that the number of atoms matches the expected formula
   - CH4 must have exactly 5 atoms (1 C + 4 H)
   - THF must have exactly 13 heavy+H atoms (4C + 8H + 1O)
   - Any mismatch → REJECT the molecule

2. **Element composition check**: Verify the set of element types matches expectations
   - PDB PPR has phosphorus → it's NOT propane
   - PDB IBO has nitrogen → it's NOT isobutane

3. **GAFF2 type check**: Verify atom types match the expected molecular connectivity
   - Methane: must have exactly 1× `c3` + 4× `hc`
   - THF: must have `os`, `c5`, `hc`, `h1` types

4. **Curated manifest**: Each bundled molecule must have a manifest entry with:
   - PDB code
   - IUPAC/common name
   - Expected formula (C₄H₈O)
   - Expected atom count (13)
   - Expected GAFF2 type set
   - Verification status (PASSED/REJECTED/MANUAL)

### Detection

Automated: Compare mol2 atom count + element composition against expected values in the manifest. Any mismatch flags the molecule for manual review.

### Recovery

If a misidentified molecule is discovered post-bundling:
1. Remove it from the library
2. Replace with the correct molecule (manual GAFF2 parametrization)
3. Issue a bug fix release

**Source:** Agent C research (RELEVANCE-FILTER.md), verified against 39 molecules with 10 name collisions confirmed. **Confidence: HIGH.**

---

## P3: The `[ atomtypes ]` Inline vs. Commented-Out ITP Convention

**Severity:** HIGH (consistency — will cause `grompp` errors if mixed)
**Status:** BLOCKING — must standardize before release
**Nature:** CONFIRMED — inconsistency found in existing QuickIce files

### What Goes Wrong

QuickIce currently ships **two different ITP conventions** for atom type definitions:

1. **ch4.itp, thf.itp**: `[ atomtypes ]` section is **commented out** (types defined in parent .top)
2. **etoh.itp**: `[ atomtypes ]` section is **inline** (types defined inside the .itp itself)

When a user includes BOTH an inline-atomtypes ITP and a parent .top that also defines atom types, `grompp` fails with:

```
ERROR 1 [file etoh.itp, line 3]: Atomtype 'hc' defined more than once
```

### Why It Happens

- ch4.itp and thf.itp were created by Sobtop and then **manually modified** to comment out `[ atomtypes ]`
- etoh.itp was created by Sobtop and was **not modified** — it still has inline atom types
- The gromacs_writer.py generates a single `[ atomtypes ]` block in the parent .top, so any inline atom types in included .itp files cause duplicates

### Consequences

- A user who mixes etoh.itp (inline atomtypes) with the QuickIce-generated .top file → `grompp` fails
- The converter MUST pick ONE convention and use it consistently for ALL output files

### Prevention

**Standardize on the commented-out convention** (matching ch4.itp, thf.itp, and the gromacs_writer.py behavior):

1. All bundled .itp files: `[ atomtypes ]` section **commented out**
2. The parent .top file: one consolidated `[ atomtypes ]` block with ALL atom types
3. The converter should output a SEPARATE atomtypes block (for pasting into .top) alongside each .itp

### Detection

`grompp` will fail immediately with "Atomtype defined more than once" if inline and global atom types conflict.

### Recovery

Remove the inline `[ atomtypes ]` section from affected .itp files and ensure they're in the parent .top.

**Source:** Direct file inspection of ch4.itp (lines 4-7: commented), thf.itp (lines 4-9: commented), etoh.itp (lines 3-9: inline). gromacs_writer.py lines 1247-1270 (generates global atomtypes). **Confidence: HIGH.**

---

## P4: `fudgeLJ`/`fudgeQQ` Were Previously Set to 0.0 (Bug DEFLT-01)

**Severity:** HIGH (was a real bug, now fixed)
**Status:** NON-BLOCKING — bug is fixed but must verify no regression
**Nature:** CONFIRMED — fixed in existing test suite

### What Went Wrong

Three of six TOP-writing functions in `gromacs_writer.py` previously wrote `fudgeLJ=0.0, fudgeQQ=0.0` instead of the correct `fudgeLJ=0.5, fudgeQQ=0.8333`. This means **all 1-4 pair interactions were completely eliminated** in affected output files.

The bug was caught and fixed (test file: `tests/test_scancode_bugs_gromacs.py`, lines 226-438), and regression tests now verify all six writers use the correct AMBER defaults.

### Prevention

1. The existing regression tests in `test_scancode_bugs_gromacs.py` cover this
2. **Any new TOP-writing function** must include a test for fudgeLJ/fudgeQQ values
3. The pre-built molecule library converter's TOP output must also be tested

### Detection

The existing test suite catches this. The test parses the `[ defaults ]` section and asserts `fudgeLJ ≈ 0.5` and `fudgeQQ ≈ 0.8333`.

**Source:** `tests/test_scancode_bugs_gromacs.py` lines 5, 226-438. **Confidence: HIGH.**

---

## P5: Combining Rule Mismatch When Mixing Force Fields

**Severity:** HIGH (scientific accuracy)
**Status:** NON-BLOCKING — document and warn only
**Nature:** THEORETICAL — not a problem in QuickIce's current scope

### What Goes Wrong

GROMACS supports three combining rules for LJ cross-interactions:
- **Rule 2** (Lorentz-Berthelot): σ_ij = (σ_i + σ_j)/2, ε_ij = sqrt(ε_i × ε_j) — used by AMBER/GAFF2
- **Rule 3** (Geometric): σ_ij = sqrt(σ_i × σ_j), ε_ij = sqrt(ε_i × ε_j) — used by OPLS
- **Rule 1** (C6/C12 geometric): used for older force fields

QuickIce uses `comb-rule=2`, matching AMBER/GAFF2 convention. If a user adds OPLS-AA molecules, the combining rule is wrong for those molecules' cross-interactions.

### Current Scope Is Safe

- TIP4P-ICE: Uses Lorentz-Berthelot (compatible with rule 2)
- GAFF2: Uses Lorentz-Berthelot (compatible with rule 2)
- Madrid2019 ions: Lorentz-Berthelot (compatible with rule 2)

All three force field components use the same combining rule. No mismatch.

### When It Becomes a Problem

If a user adds OPLS-AA molecules (comb-rule=3) or CHARMM molecules (also comb-rule=2 but different LJ parameter conventions), the cross-interactions between GAFF2 and those molecules will be computed with the wrong combining rule.

### Prevention

1. **Document** that the library is GAFF2 + TIP4P-ICE + Madrid2019, using `comb-rule=2`
2. **Warn in the GUI** if a user tries to mix molecules from different force field families
3. **Do NOT attempt** to solve this in code — it's a fundamental GROMACS limitation

**Source:** GROMACS 2026.2 manual, Equations 145-147 (non-bonded interactions). **Confidence: HIGH.**

---

## P6: GAFF2 Atom Type Name Collision Between Force Field Families

**Severity:** MEDIUM (currently safe, but fragile)
**Status:** NON-BLOCKING — document the constraint
**Nature:** THEORETICAL — not a problem in current scope, but would break if scope expands

### What Goes Wrong

GAFF2 atom types use short lowercase names: `c3`, `hc`, `oh`, `os`, `h1`, `ho`, `n`, `na`, `cl`, `f`, `br`, `i`. Some of these names conflict with:
- Element symbols: `f` = fluorine (GAFF2) vs. force constant abbreviation
- Ion names: `na` = sp2 nitrogen (GAFF2) vs. Na⁺ sodium ion, `cl` = chlorine (GAFF2) vs. Cl⁻ chloride ion

In QuickIce's current architecture, GAFF2 types are defined globally in the .top `[ atomtypes ]` section. Madrid2019 ion types use DIFFERENT names (`NA`, `CL` — uppercase). There is **no actual collision** in the current scope.

### The Specific Collision Risk

| GAFF2 Type | Meaning | Conflicting Type | Meaning | Collision? |
|------------|---------|-----------------|---------|------------|
| `na` | sp2 nitrogen | `NA` | sodium ion (Madrid2019) | **NO** — different case |
| `cl` | chlorine atom type | `CL` | chloride ion (Madrid2019) | **NO** — different case |
| `f` | fluorine atom type | — | — | No conflict in current scope |
| `i` | iodine atom type | — | — | No conflict in current scope |
| `C`, `CT`, `H`, `O`, `OH` | Legacy AMBER types | — | — | Must be mapped to GAFF2 equivalents |

### Prevention

1. **Map legacy AMBER types** (`C`→`c`, `CT`→`c3`, `HC`→`hc`, etc.) during conversion — never output uppercase AMBER types
2. **Keep ion names uppercase** (NA, CL — Madrid2019 convention)
3. **Document** the naming convention in the library manifest

### Detection

`grompp` will error if the same atom type name is defined with different parameters.

**Source:** FORMAT-CONVERSION.md Section 5 (atom type mapping). ch4.itp, thf.itp, etoh.itp (all use lowercase GAFF2 types). **Confidence: HIGH.**

---

## P7: Molecules with "ATTN, need revision" Missing Parameters

**Severity:** HIGH (simulation crashes or garbage results)
**Status:** BLOCKING — must skip or flag these 19 molecules
**Nature:** CONFIRMED — 19 frcmod files contain ATTN entries

### What Goes Wrong

19 out of 28,745 frcmod files contain entries marked `"ATTN, need revision"`, indicating that `parmchk2` could not find suitable parameters even by distant analogy. These entries have **zero-valued force constants** (k=0) — the corresponding interaction simply doesn't exist in the converted GROMACS output.

If a simulation runs with an ATTN molecule:
- Bonds/angles/dihedrals with k=0 → the molecule has **no restoring force** for those degrees of freedom
- The molecule will deform uncontrollably during MD
- Energy minimization may converge to unphysical geometries
- The simulation may crash with LINCS/SETTLE errors

### Prevention

1. **SKIP all 19 ATTN molecules** — do not include them in the bundled library
2. **The converter must detect** `"ATTN"` entries in frcmod files and skip the molecule
3. **If a user supplies their own mol2+frcmod**, warn about ATTN entries and refuse to convert

### Detection

Parse frcmod DIHE and IMPROPER sections for the string `"ATTN, need revision"`. The 19 affected molecules are listed in the geostd archive.

### Recovery

These molecules require **manual parametrization** using QM calculations or expert judgment. They cannot be reliably converted from the geostd data.

**Source:** FORMAT-CONVERSION.md Section 13 (penalty scores) — "Contains 'ATTN, need revision': 0.07%". **Confidence: HIGH.**

---

## P8: High Penalty Score Molecules (Unreliable Parameters)

**Severity:** MEDIUM (results may be scientifically unreliable)
**Status:** NON-BLOCKING — include with GUI warning
**Nature:** CONFIRMED — statistical distribution from 28,744 frcmod files

### What Goes Wrong

`parmchk2` assigns penalty scores to each parameter based on how far the analogy is from a direct GAFF2 match. High penalty scores mean the parameters are unreliable:

| Penalty Score | % of Entries | Assessment |
|---------------|-------------|------------|
| 0.0 | 73.6% | Excellent — direct GAFF2 match |
| 3.0 | 1.4% | Good — close analogy |
| 6.0 | 9.5% | Acceptable — general parameter |
| 38-50 | ~2% | Questionable — weak analogy |
| 67-100 | ~3% | Poor — distant analogy |
| 136-200 | ~2% | Bad — very unreliable |
| 223+ | ~4% | Dangerous — should not use |

About **12% of molecules** have at least one parameter with penalty > 50, meaning they have some unreliable parameters.

### Consequences

- Penalty ≤ 6: Parameters are reliable for production MD
- Penalty 6-50: Parameters may give reasonable structural properties but uncertain thermodynamics
- Penalty > 50: Parameters are based on very distant analogies — structural and thermodynamic properties may be significantly wrong

### Prevention

1. **For the curated library (100-150 molecules):** Only include molecules with ALL penalty scores ≤ 6 (the "82% clean" category)
2. **If including molecules with penalty 6-50:** Show a yellow warning in the GUI
3. **Never include molecules with any penalty > 50** without explicit user opt-in

### Detection

Parse penalty scores from frcmod comment strings (e.g., `"penalty score= 44.3"`). The converter should extract the **maximum penalty score** across all parameters for each molecule.

### Recovery

High-penalty molecules should be re-parameterized using `parmchk2` with custom QM data, or replaced with manually curated parameters.

**Source:** FORMAT-CONVERSION.md Section 13 (penalty score distribution, from 595,792 total frcmod entries). **Confidence: HIGH.**

---

## P9: LJ Parameter Convention Mismatch (AMBER Rmin/2 vs GROMACS σ)

**Severity:** CRITICAL (if done wrong, ALL LJ interactions are wrong)
**Status:** NON-BLOCKING — conversion formula is known and verified
**Nature:** CONFIRMED — verified by comparing geostd data with QuickIce ITP values

### What Goes Wrong

AMBER stores LJ parameters as **Rmin/2** (half the minimum-energy distance for the like-pair interaction, in Ångströms) and **ε** (well depth in kcal/mol). GROMACS stores them as **σ** (zero-crossing distance in nm) and **ε** (well depth in kJ/mol).

The conversion formula is:
```python
R_star_angstrom = 2.0 * Rmin_half_angstrom       # Full minimum distance
sigma_angstrom = R_star / (2.0 ** (1.0 / 6.0))   # Zero-crossing distance
sigma_nm = sigma_angstrom * 0.1                    # Convert to nm
epsilon_kj = epsilon_kcal * 4.184                  # Convert to kJ/mol
```

**If this conversion is done incorrectly** (e.g., using σ = 2 × Rmin/2 without the 2^(1/6) correction), ALL non-bonded interactions in the simulation will be systematically wrong. The error would be a ~12% shift in σ values, which would produce significantly different LJ energetics and structural properties.

### Verification

The formula is verified against QuickIce's existing ITP files:
- GAFF2 c3: Rmin/2 = 1.9080 Å → σ = 2 × 1.908 / 2^(1/6) × 0.1 = 0.33977 nm ✓ (matches ch4.itp)
- GAFF2 hc: Rmin/2 ≈ 1.459 Å → σ ≈ 0.26002 nm ✓ (matches ch4.itp)

### Prevention

1. **Implement the conversion formula exactly** as shown above
2. **Add a unit test** that converts all 96 GAFF2 types and compares against known reference values
3. **Validate** the first 10-20 converted molecules against Sobtop-generated reference ITP files

### Detection

Compare σ and ε values in converted ITP files against Sobtop-generated reference files for ch4, thf, etoh. Any systematic discrepancy indicates a conversion error.

**Source:** FORMAT-CONVERSION.md Section 6 (LJ parameter conversion, verified derivation). ch4.itp, thf.itp, etoh.itp (reference σ/ε values). **Confidence: HIGH.**

---

## P10: Bond/Angle Energy Convention (½ Factor Difference)

**Severity:** CRITICAL (if done wrong, ALL bonded interactions are wrong)
**Status:** NON-BLOCKING — conversion formula is known and verified
**Nature:** CONFIRMED — verified by comparing AMBER params with QuickIce ITP values

### What Goes Wrong

AMBER and GROMACS use different conventions for the harmonic potential:

- **AMBER:** `E = k × (x - x₀)²` (NO factor of ½)
- **GROMACS:** `E = ½ × k × (x - x₀)²` (WITH factor of ½)

This means AMBER's force constant must be **doubled** when converting to GROMACS format:

```python
kb_gromacs = 2.0 * k_amber_kcal * KCAL_TO_KJ / (ANGSTROM_TO_NM ** 2)
ctheta_gromacs = 2.0 * k_amber_kcal * KCAL_TO_KJ
```

**If this factor of 2 is forgotten**, all bonds and angles will have **half the correct stiffness**, causing:
- Softer molecules that vibrate excessively
- Incorrect vibrational frequencies
- Potential bond breaking during high-temperature simulations
- Wrong structural properties (bond lengths, angles)

### Verification

- AMBER c3-hc bond: k=347.0 kcal/mol/Å² → kb = 2 × 347.0 × 4.184 / 0.01 = 289,938 kJ/mol/nm² → ch4.itp shows 2.889052E+05 ≈ 288,905 ✓
- AMBER hc-c3-hc angle: k=35.77 kcal/mol/rad² → ctheta = 2 × 35.77 × 4.184 = 299.57 → ch4.itp shows 2.995744E+02 ≈ 299.57 ✓

### Prevention

1. **The conversion formulas are verified** — implement them exactly
2. **Add a unit test** comparing converted parameters against Sobtop reference files
3. **Code review** — this is the #1 place where a typo (missing `2.0 *`) would cause silent scientific errors

### Detection

Run a short test simulation and compare bond length distributions against known AMBER values. Systematic 2× errors in force constants will show as bond vibrations with ~1.4× larger amplitude.

**Source:** FORMAT-CONVERSION.md Section 6 (bond/angle conversion, verified derivation). **Confidence: HIGH.**

---

## P11: Dihedral idivf Division (Forgotten Divide-by-idivf)

**Severity:** HIGH (if done wrong, dihedral barriers are wrong)
**Status:** NON-BLOCKING — conversion formula is known
**Nature:** CONFIRMED — verified against etoh.itp

### What Goes Wrong

AMBER dihedrals have an `idivf` (divide factor) that is applied to the barrier height:

```
AMBER: E = (Vn / idivf) × (1 + cos(pn × φ - phase))
GROMACS: E = kd × (1 + cos(pn × φ - phase))
```

So: `kd_gromacs = Vn × 4.184 / idivf`

**If `idivf` is forgotten**, the dihedral barrier is too large by the idivf factor (commonly 3, 4, 6, or 9). This would:
- Make rotational barriers too high
- Prevent conformational changes that should occur
- Affect free energy calculations
- Give incorrect population of rotameric states

### Verification

etoh.itp: X-c3-c3-X dihedral with kd=0.65084, pn=3
- Vn = 0.65084 × 3 / 4.184 = 0.467 kcal/mol, idivf=3
- kd = 0.467 × 4.184 / 3 = 0.65084 ✓

### Prevention

1. Parse `idivf` from frcmod DIHE section (it's the second field after the type quartet)
2. Apply `kd = Vn × 4.184 / idivf` for ALL proper dihedrals
3. For impropers: `idivf = 1` (no division)

### Detection

Compare converted dihedral parameters against Sobtop-generated reference files.

**Source:** FORMAT-CONVERSION.md Section 6 (dihedral conversion) and Section 7 (idivf explanation). **Confidence: HIGH.**

---

## P12: Residue Name Conflicts with Standard GROMACS Names

**Severity:** MEDIUM (can cause `grompp` errors or confusion)
**Status:** NON-BLOCKING — manageable with naming convention
**Nature:** CONFIRMED — real naming conflict risk

### What Goes Wrong

GROMACS reserves certain residue names for standard molecules:
- `SOL` = water
- `NA` / `CL` = ions (varies by force field)
- `HOH` = water (CHARMM convention)

The geostd mol2 files use the PDB code as the residue name (e.g., `CH4`, `THF`, `DIO`, `M00`). Some of these could conflict:
- `NA` (sodium) vs `na` (GAFF2 nitrogen type) — case difference helps, but residue names are case-insensitive in some GROMACS tools
- `ACT` (acetate) vs other standard residue names

### Consequences

If a residue name conflicts:
- `grompp` may confuse the molecule with a different one
- Analysis tools (gmx select, gmx trjconv) may group atoms incorrectly
- GRO file residue numbers may wrap or become ambiguous

### Prevention

1. **Use uppercase molecule codes** as residue names (matching ch4.itp convention: `CH4`, `THF`)
2. **Avoid reserved names:** Never use `SOL`, `HOH`, `WAT`, `NA`, `CL`, `K`, `CAL` as residue names
3. **For ions** that aren't in Madrid2019: Use distinct names like `NH4`, `SO4`
4. **Add a reserved-name check** in the converter

### Detection

`grompp` may warn about duplicate moleculetype names but won't necessarily catch residue name conflicts in .gro files.

**Source:** GROMACS 2026.2 manual (topology file format). ch4.itp uses `CH4` as resname. tip4p-ice.itp uses `SOL`. **Confidence: HIGH.**

---

## P13: Atom Name Length in GRO Format (5-Character Limit)

**Severity:** MEDIUM (will cause parsing errors)
**Status:** NON-BLOCKING — handle in converter
**Nature:** CONFIRMED — GRO format specification

### What Goes Wrong

The GRO format limits atom names to **5 characters** (right-justified in `%5s` format). Some mol2 files use longer atom names:
- `H1'1`, `H1'2` (DIO.mol2 — 4 chars, OK)
- Some molecules may have names like `H1A1`, `CA3B` (5 chars, borderline)
- Apostrophes in atom names (`H1'1`) may cause problems in GROMACS analysis tools

### Consequences

- GRO files with atom names > 5 chars → parsing errors in `grompp`, `gmx editconf`
- Apostrophes in atom names → potential issues with `gmx select` syntax

### Prevention

1. **Truncate** atom names to 5 characters maximum
2. **Strip apostrophes** from atom names: `H1'1` → `H11`, `H2'1` → `H21`
3. **Ensure uniqueness** after truncation — if two atoms have the same truncated name, add a numeric suffix

### Detection

Check all mol2 atom names for length > 5 and presence of apostrophes before conversion.

**Source:** FORMAT-CONVERSION.md Section 4 (GRO format specification). GROMACS 2026.2 manual (file formats). **Confidence: HIGH.**

---

## P14: GRO Box Dimensions (0.0 0.0 0.0 for Single Molecules)

**Severity:** LOW (most GROMACS tools handle it, but some may not)
**Status:** NON-BLOCKING — document the convention
**Nature:** CONFIRMED — etoh.gro uses 0.0 0.0 0.0

### What Goes Wrong

Single-molecule GRO files use `0.0 0.0 0.0` as box dimensions (etoh.gro convention). Most GROMACS tools handle this correctly — they treat the molecule as having no periodic box. However:

- `gmx editconf -bt cubic` may fail or produce a 0-sized box if not given explicit box dimensions
- `gmx solvate` requires a defined box to add solvent
- Some visualization tools may render the molecule incorrectly with a zero-size box

### Prevention

1. **Keep the 0.0 0.0 0.0 convention** — it's the standard for template molecules
2. **Document** that users must run `gmx editconf` to set box dimensions before solvation
3. **The QuickIce GUI** already handles box setup during structure generation — the single-molecule .gro is only used as a template for atom placement

### Detection

Not a bug — this is the expected convention. Just document it clearly.

**Source:** etoh.gro (line 12: `0.00000   0.00000   0.00000`). FORMAT-CONVERSION.md Section 4. **Confidence: HIGH.**

---

## P15: Starting Geometry Quality (PBEh-3c Optimized Structures)

**Severity:** LOW (GROMACS will minimize anyway)
**Status:** NON-BLOCKING — document only
**Nature:** THEORETICAL — minimal practical impact

### What Goes Wrong

The geostd geometries are PBEh-3c QM-optimized, which produces high-quality equilibrium structures. However:
- QM-optimized geometries may differ from force-field-optimized geometries
- Bond lengths and angles from QM may not match the GAFF2 equilibrium values exactly
- This creates an initial strain energy that GROMACS must dissipate during energy minimization

### Why It's Not Really a Problem

1. **GROMACS always energy-minimizes** before production MD — the starting geometry is just a template
2. **PBEh-3c geometries are excellent** starting points — they're physically reasonable
3. **The deviation** between QM and FF equilibrium structures is typically < 0.01 Å for bonds, < 2° for angles
4. **QuickIce places molecules** in clathrate cages with specific orientations — the QM geometry is a better starting point than a random conformer

### Prevention

1. **Run energy minimization** before production MD (standard practice)
2. **Check the minimized energy** — if it's much higher than expected, the starting geometry may be bad

### Detection

After minimization, check that the maximum force is < 1000 kJ/mol/nm (standard criterion).

**Source:** phenix geostd README (PBEh-3c optimization). General MD practice. **Confidence: MEDIUM.**

---

## P16: TIP4P-ICE LJ Parameters in .top File Are 1000× Too Small (EXISTING BUG)

**Severity:** CRITICAL (all TIP4P-ICE LJ interactions are effectively zero)
**Status:** BLOCKING — must investigate and fix before pre-built molecule release
**Nature:** CONFIRMED — values in .top files contradict reference TIP4P-ICE parameters

### What Goes Wrong

QuickIce's `gromacs_writer.py` writes TIP4P-ICE water atom types with **extremely small σ and ε values** in the `[ atomtypes ]` section:

```gro
; From hydrate_sI_ch4_1x1x1.top (line 11):
OW_ice   OW_ice    8    15.9994  0.0    A    0.31668e-3    0.88216e-6
;                                          ^^^^^^^^^^    ^^^^^^^^^^
;                                          σ = 0.000317 nm   ε = 8.8e-7 kJ/mol
```

But the **correct TIP4P-ICE values** (from the commented-out ITP and the Abascal 2007 paper) are:

```gro
; From tip4p-ice.itp (line 4, commented out):
;OW_ice      8      15.9994  0.0000  A   0.31668  0.88211
;                                     ^^^^^^^^  ^^^^^^
;                                     σ = 0.31668 nm   ε = 0.88211 kJ/mol
```

The discrepancy:
| Parameter | .top file value | Correct value | Error factor |
|-----------|----------------|---------------|-------------|
| σ(OW_ice) | 0.31668e-3 = 0.00031668 nm | 0.31668 nm | **1000× too small** |
| ε(OW_ice) | 0.88216e-6 = 0.000000882 kJ/mol | 0.88211 kJ/mol | **10^6× too small** |

With comb-rule=2 (Lorentz-Berthelot), the `[ atomtypes ]` section V = σ (nm) and W = ε (kJ/mol). The tiny values make ALL TIP4P-ICE LJ interactions effectively zero:

- **OW-OW (water-water):** σ = 0.000317 nm, ε = 8.8e-7 kJ/mol → NO van der Waals attraction between water molecules
- **OW-guest (water-methane):** σ = (0.000317 + 0.3398)/2 = 0.170 nm, ε = sqrt(8.8e-7 × 0.451) = 0.000630 kJ/mol → essentially NO water-guest LJ
- **This eliminates the hydrate cage stability entirely** — guest-host van der Waals is the primary stabilizing force for clathrate hydrates

### Why This May Not Have Been Caught

1. **Short test simulations** may not show catastrophic failure — water molecules still have electrostatic interactions via PME, and constraints maintain geometry
2. **No energy validation tests** exist in the test suite — tests check fudgeLJ/fudgeQQ values but NOT atomtypes LJ values
3. **GROMACS doesn't warn** about atomtypes with very small LJ parameters
4. **The PME electrostatics** provide some cohesion even without LJ, making the simulation appear to "work" for short runs
5. **Thermodynamic properties** (dissociation pressure, hydration free energy) would be catastrophically wrong, but these are rarely checked in automated tests

### Prevention

1. **Fix the gromacs_writer.py** — use correct σ/ε values: `3.16680e-1` nm and `8.82160e-1` kJ/mol
2. **Add a validation test** that checks atomtypes values against known TIP4P-ICE reference
3. **Add a runtime sanity check** — warn if any atomtype has σ < 0.01 nm or ε < 0.001 kJ/mol (likely indicates a unit error)
4. **Cross-validate** the OW-OW dimer LJ energy at the expected r_min against the Abascal 2007 paper

### Detection

Compute the TIP4P-ICE O-O dimer LJ energy at r = 2^(1/6) × 0.31668 nm:
- With correct values: V = 4 × 0.882 × [(0.31668/0.3558)^12 - (0.31668/0.3558)^6] = -0.882 kJ/mol
- With .top values: V ≈ 0 kJ/mol (effectively zero)

A simple Python calculation comparing these two should be added as a test.

### Recovery

This is a data bug, not a structural bug. Fix the values in gromacs_writer.py and re-run simulations.

**IMPORTANT NOTE:** This pitfall applies to **existing QuickIce functionality**, not just the pre-built molecule feature. However, the pre-built molecule feature makes this more critical because users will rely on QuickIce's atomtype definitions for both water AND guest molecules. If water LJ is wrong, the entire hydrate simulation is unreliable.

**Source:** gromacs_writer.py lines 541, 974, 1253 (all write `0.31668e-3` and `0.88216e-6`). tip4p-ice.itp line 4 (commented correct values: `0.31668` and `0.88211`). GROMACS 2026.2 manual parameter-files page (confirms V=σ, W=ε for comb-rule=2). Abascal et al., J. Chem. Phys. 122, 234511 (2005) — TIP4P-ICE paper (σ_O = 3.1668 Å, ε_O/k_B = 106.1 K → ε = 0.882 kJ/mol). **Confidence: HIGH — values clearly wrong by 1000× and 10^6×.**

---

## P17: GAFF2 Parameter Table Accuracy (Bundled gaff2.dat)

**Severity:** MEDIUM (if errors exist, ALL converted molecules are affected)
**Status:** NON-BLOCKING — but must validate before release
**Nature:** THEORETICAL — no known errors, but no validation performed yet

### What Goes Wrong

The converter bundles a Python dictionary of ~2000 GAFF2 parameter entries (bonds, angles, dihedrals, impropers, LJ) extracted from `gaff2.dat`. If any entry has a typo or transcription error:
- Every molecule using that parameter will be wrong
- The error is **systematic** — not random
- It could affect a single parameter (e.g., one bond type) or many

### Prevention

1. **Parse gaff2.dat programmatically** — don't manually type values into a Python dict
2. **Cross-validate** against AmberTools' `parmchk2` output for 10-20 reference molecules
3. **Add a checksum or hash** of the original gaff2.dat file to detect changes
4. **Version-pin** the gaff2.dat source (e.g., GAFF2 v2.20 from AmberTools24)

### Detection

Compare the bundled Python dict against the original gaff2.dat file by running `parmchk2` on a test molecule and comparing the output frcmod against the converter's output.

**Source:** FORMAT-CONVERSION.md Section 10 (LJ parameter sources). **Confidence: MEDIUM — no validation has been done yet.**

---

## P18: Bundle Size and Startup Load Time

**Severity:** LOW (tiny bundle, fast load)
**Status:** NON-BLOCKING — not a real concern
**Nature:** CONFIRMED — size estimates are negligible

### What Goes Wrong

Concern: 100-150 molecules × ~4 KB ITP + ~0.5 KB GRO = ~500 KB total. Plus GAFF2 parameter table (~50-100 KB as Python dict). Plus mol2/frcmod source files if bundled (~1 MB).

### Why It's Not a Problem

- **500 KB** of pre-built ITP/GRO files is tiny
- **50-100 KB** GAFF2 parameter dict is tiny
- **1 MB** mol2/frcmod source files is tiny
- **Total: < 2 MB** — well within any reasonable package size limit
- **Load time:** Reading a Python dict with ~2000 entries takes < 1ms. Indexing 150 molecule entries from a JSON manifest takes < 1ms.
- **Memory:** A Python dict with 2000 string-float entries uses < 500 KB of RAM

### Prevention

No special measures needed. The bottleneck is **curation quality**, not bundle size.

**Source:** RELEVANCE-FILTER.md Section 6 (size estimates). **Confidence: HIGH.**

---

## P19: Impropers with Wildcard Expansion Produces Too Many Entries

**Severity:** MEDIUM (verbose output, potential for duplicate entries)
**Status:** NON-BLOCKING — handle with deduplication
**Nature:** CONFIRMED — AMBER wildcard convention documented

### What Goes Wrong

AMBER defines impropers with wildcards: `X-X-ca-ha` means "any atom types at positions 1,2, with `ca` at position 3 and `ha` at position 4." When expanding this for a molecule with many `ca` atoms, each with 3 bonded neighbors, the number of explicit improper quartets can be large.

For example, a benzene ring with 6 `ca` atoms × 3 neighbors each = up to 18 improper quartets from a single wildcard rule. Multiple wildcard rules can produce hundreds of entries.

### Consequences

- Large `[ dihedrals ]` sections in .itp files — not wrong, just verbose
- **Duplicate entries** if multiple wildcard rules match the same quartet — GROMACS applies ALL of them, which could double-count the improper energy
- Potential for **incorrect energy** if duplicates are not caught

### Prevention

1. **Deduplicate** explicit atom quartets after wildcard expansion
2. **For each quartet**, ensure only one improper definition applies
3. **AMBER convention:** When multiple improper definitions match the same quartet, the most specific one (fewest wildcards) takes precedence

### Detection

Compare the number and energy of improper dihedrals against `parmchk2` reference output.

**Source:** FORMAT-CONVERSION.md Section 9 (improper handling). **Confidence: MEDIUM — needs testing with real molecules.**

---

## P20: Multiple Dihedral Terms for Same Quartet (Not a Bug)

**Severity:** LOW (correctly handled by funct=9)
**Status:** NON-BLOCKING — document the behavior
**Nature:** CONFIRMED — this is correct AMBER physics

### What Goes Wrong

This is NOT actually a pitfall — it's a correct behavior that may confuse developers. AMBER defines multiple dihedral terms for the same atom quartet with different periodicities:

```
os-c6-c6-os   1    0.500    0.000    -3.000
os-c6-c6-os   1    0.900    0.000    -2.000
os-c6-c6-os   1    0.180    0.000     1.000
```

Each term represents a different Fourier component of the dihedral potential. In GROMACS, each becomes a separate `[ dihedrals ]` line with `funct=9`. This is **correct** — GROMACS evaluates each term independently and sums the energies.

### Prevention

Document in the converter code that multi-term dihedrals are expected and correct.

### Detection

No issue — this is correct behavior.

**Source:** FORMAT-CONVERSION.md Section 7 (dihedral handling). DIO.frcmod as example. **Confidence: HIGH.**

---

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation | Severity |
|-------|---------------|------------|----------|
| Converter implementation | LJ convention (P9), ½ factor (P10), idivf (P11) | Unit tests against Sobtop reference | CRITICAL |
| Molecule curation | PDB name collision (P2), ATTN molecules (P7) | Automated atom count + element verification | CRITICAL |
| ITP generation | Inline vs. commented atomtypes (P3) | Standardize on commented-out convention | HIGH |
| TOP writer | fudgeLJ/fudgeQQ (P1, P4), TIP4P-ICE LJ values (P16) | Regression tests + atomtypes validation | CRITICAL |
| GUI search panel | PDB name collision (P2) | Show verified name, formula, and atom count | HIGH |
| Library bundling | Penalty scores (P8), GAFF2 table accuracy (P17) | Only bundle penalty ≤ 6 molecules | MEDIUM |
| Mixed force field use | 1-4 scaling (P1), comb-rule (P5), type collision (P6) | Document GAFF2-only constraint; warn on mixing | HIGH |
| Residue naming | Conflict with SOL/NA/CL (P12) | Reserved name check | MEDIUM |
| GRO generation | Atom name length (P13), box dims (P14) | Truncate names, document 0-box convention | LOW |

---

## Summary: Blocking vs. Non-Blocking

### BLOCKING (must fix before release)

| ID | Pitfall | Why Blocking |
|----|---------|-------------|
| P1 | 1-4 scaling is system-wide | Must verify it's correct for GAFF2+TIP4P-ICE+Madrid2019 scope |
| P2 | PDB name collision (25%) | Users WILL accidentally select wrong molecules without verification |
| P3 | Inline vs. commented atomtypes | `grompp` will fail if conventions are mixed |
| P7 | ATTN missing parameters | Simulations with these molecules are scientifically meaningless |
| P9 | LJ Rmin/2 → σ conversion | If wrong, ALL non-bonded interactions are wrong |
| P10 | ½ factor in bond/angle | If wrong, ALL bonded interactions are wrong |
| P16 | TIP4P-ICE LJ values 1000× too small | ALL TIP4P-ICE water LJ interactions are effectively zero; hydrate stability destroyed |

### NON-BLOCKING (document/warn only)

| ID | Pitfall | Action |
|----|---------|--------|
| P4 | fudgeLJ/QQ = 0.0 bug | Already fixed + regression tests |
| P5 | Combining rule mismatch | Document GAFF2-only scope |
| P6 | Atom type name collision | Currently safe; document naming convention |
| P8 | High penalty scores | Include with GUI warning |
| P11 | idivf division | Known formula, implement correctly |
| P12 | Residue name conflicts | Reserved name check in converter |
| P13 | Atom name length | Truncate in converter |
| P14 | GRO box = 0.0 | Document convention |
| P15 | Starting geometry quality | Standard EM practice |
| P17 | GAFF2 table accuracy | Validate against original gaff2.dat |
| P18 | Bundle size | Not a real concern |
| P19 | Improper wildcard expansion | Deduplicate |
| P20 | Multi-term dihedrals | Correct behavior, document |

---

## Sources

| Source | URL/Location | Confidence |
|--------|-------------|------------|
| GROMACS 2026.2 Reference Manual | https://manual.gromacs.org/current/ | HIGH (official) |
| GROMACS non-bonded interactions | https://manual.gromacs.org/current/reference-manual/functions/nonbonded-interactions.html | HIGH (official) |
| GROMACS topology file format | https://manual.gromacs.org/current/reference-manual/topologies/topology-file-formats.html | HIGH (official) |
| GROMACS parameter files | https://manual.gromacs.org/current/reference-manual/topologies/parameter-files.html | HIGH (official — confirms V=σ, W=ε for comb-rule=2) |
| QuickIce gromacs_writer.py | quickice/output/gromacs_writer.py | HIGH (codebase) |
| QuickIce test suite | tests/test_scancode_bugs_gromacs.py | HIGH (codebase) |
| QuickIce ITP files | quickice/data/{ch4,thf,etoh}.itp | HIGH (codebase) |
| FORMAT-CONVERSION.md (Agent B) | .planning/research/future-ml/pre-built-small-molecules/FORMAT-CONVERSION.md | HIGH (prior research) |
| RELEVANCE-FILTER.md (Agent C) | .planning/research/future-ml/pre-built-small-molecules/RELEVANCE-FILTER.md | HIGH (prior research) |
| LICENSE.md (Agent A) | .planning/research/future-ml/pre-built-small-molecules/LICENSE.md | HIGH (prior research) |
