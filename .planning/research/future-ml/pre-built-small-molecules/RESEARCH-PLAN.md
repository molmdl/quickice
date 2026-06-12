# Research Plan: Pre-built Small Molecules for GROMACS

**Feature:** Library of pre-built small molecules (from AMBER geostd) converted to GROMACS format, with GUI search/browse panel
**Output dir:** `.planning/research/future-ml/pre-built-small-molecules/`
**Total agents:** 5 agents across 3 waves
**Date:** 2026-06-12

---

## Wave Structure

```
Wave 1 (parallel):  Agent A (License)  +  Agent B (Format Conversion)
                            \                    /
Wave 2 (sequential):     Agent C (Relevance Filter — depends on A+B)
                            |
Wave 3 (sequential):     Agent D (Architecture)  +  Agent E (Pitfalls)
                            \                    /
                          Agent F (SYNTHESIS — depends on all)
```

| Wave | Agents | Parallelism | Dependencies |
|------|--------|-------------|--------------|
| 1 | A (License), B (Format Conversion) | Parallel | None |
| 2 | C (Relevance Filter) | Sequential after Wave 1 | Needs license clarity from A; needs conversion feasibility from B |
| 3 | D (Architecture), E (Pitfalls) | Parallel | Need conversion approach from B; relevance scope from C |
| 4 | F (Synthesis) | Sequential after Wave 3 | Consumes all prior outputs |

---

## Agent A: License & Redistribution Research

**Wave:** 1 (parallel, no dependencies)
**Output files:** `LICENSE.md`, `SUMMARY-A.md`
**Estimated research time:** 30-45 min

### Key Questions

1. **AMBER geostd license terms:** What is the exact license for the geostd data files? The README references AmberTools24 and phenix geostd — both may have different licenses.
   - Is the geostd data itself under a different license than AmberTools code?
   - Can mol2/frcmod files be redistributed as-is?
   - Can DERIVED files (.gro/.itp converted from mol2/frcmod) be redistributed under a different license?
   
2. **AmberTools license:** AmberTools is GPL-3.0 since AmberTools 2023. What does this mean for redistribution of DATA files produced by AmberTools programs (antechamber, parmchk2)?
   - Is the OUTPUT of GPL-3.0-licensed programs automatically GPL-3.0? (Legal consensus: NO — output is the user's work product, not a derivative of the program)
   - But the README says these were produced by `antechamber` and `parmchk2` from AmberTools24 — does the GPL "taint" the output?
   - Critical distinction: Using AmberTools to PRODUCE files vs. redistributing AmberTools SOURCE CODE

3. **phenix geostd license:** The starting geometries come from the phenix geostd database (https://github.com/phenix-project/geostd). What is its license?
   - Check the actual GitHub repo LICENSE file
   - Check if PDB component data (CCD) has its own terms of use

4. **PDB component library terms:** The molecules come from the PDB components library. What are the RCSB PDB terms of use for this data?
   - PDB data is generally public domain / CC0
   - But curated parameterizations may add copyrightable elements

5. **GAFF2 force field licensing:** GAFF2 is part of AmberTools. The ATOM TYPES (c3, c2, ca, oh, etc.) and force field PARAMETERS (bond lengths, angles, dihedrals) — are these redistributable?
   - QuickIce is MIT-licensed
   - Can MIT-licensed software include GAFF2 parameter data?
   - What about the frcmod file specifically — is it a derivative work of GAFF2?

6. **Redistribution strategies if GPL is an issue:**
   - Option A: Ship converted .gro/.itp files as data (not code) — does the GPL apply to data files?
   - Option B: Ship only the conversion tool, require users to download geostd separately
   - Option C: Ship a curated subset under a different justification (PDB CCD data is public domain)
   - Option D: Negotiate a license exception (unlikely for a small project)

### Sources to Consult

- `tmp/amber_geostd/README` — license references, provenance
- https://github.com/phenix-project/geostd — phenix geostd license
- https://ambermd.org/AmberTools.php — AmberTools license page
- https://www.wwpdb.org/policy — PDB terms of use
- GPL-3.0 text regarding "output of GPL programs" vs "derivative works"
- FSF FAQ on GPL and output: https://www.gnu.org/licenses/gpl-faq.html#CanIUseGPLOnlyFontsInCommercialProject
- QuickIce's own MIT LICENSE file

### Output Format

`LICENSE.md` should include:
- Section per source (AmberTools, geostd, PDB CCD, GAFF2)
- For each: exact license, what it covers, redistribution rights, restrictions
- Clear verdict: CAN or CANNOT redistribute converted files under MIT
- If CANNOT: viable workarounds (Option B, C, etc.)
- Confidence level for each verdict (HIGH/MEDIUM/LOW)

`SUMMARY-A.md`: 1-paragraph executive summary of license situation with clear go/no-go recommendation

---

## Agent B: AMBER→GROMACS Format Conversion Research

**Wave:** 1 (parallel, no dependencies)
**Output files:** `FORMAT-CONVERSION.md`, `SUMMARY-B.md`
**Estimated research time:** 45-60 min

### Key Questions

1. **mol2 format anatomy:** What are ALL the TRIPOS sections in a mol2 file? Which ones are needed for GROMACS conversion?
   - `@<TRIPOS>MOLECULE` — name, atom/bond counts, molecule type, charge method
   - `@<TRIPOS>ATOM` — atom name, x/y/z, SYBYL atom type, residue, charge
   - `@<TRIPOS>BOND` — bond indices and bond types (1=single, 2=double, ar=aromatic, am=amide)
   - `@<TRIPOS>SUBSTRUCTURE` — residue info
   - What about `@<TRIPOS>FORCE_FIELD_MISC` or other sections?

2. **frcmod format anatomy:** What are ALL sections in an frcmod file? Which provide parameters NOT already in GAFF2?
   - `MASS` — atom masses (usually empty — from GAFF2)
   - `BOND` — bond force constants and equilibrium lengths
   - `ANGLE` — angle force constants and equilibrium angles
   - `DIHE` — dihedral parameters (Vn/kn, phase, periodicity, with "same as" comments)
   - `IMPROPER` — improper dihedral parameters
   - `NONBON` — Lennard-Jones parameters (usually empty — from GAFF2)
   - What about the "penalty score" comments — are these quality indicators?

3. **GROMACS ITP target format:** What EXACT sections must a valid GROMACS .itp file contain?
   - `[ moleculetype ]` — name + nrexcl
   - `[ atoms ]` — nr, type, resnr, residue, atom, cgnr, charge, mass
   - `[ bonds ]` — ai, aj, funct, b0, kb (functype=1 for harmonic)
   - `[ angles ]` — ai, aj, ak, funct, theta0, ctheta
   - `[ dihedrals ]` — proper (functype=9 for periodic) + improper (functype=2 for harmonic)
   - `[ pairs ]` — 1-4 interactions (functype=1 for LJ+ Coulomb)
   - `[ exclusions ]` — excluded pairs
   - What about `[ atomtypes ]` — should this be in the ITP or the parent .top?

4. **GROMACS GRO target format:** What must a valid .gro file contain for a single molecule?
   - Title line, atom count, atom records, box dimensions
   - Can the box be 0.0 0.0 0.0 for a single molecule?

5. **CRITICAL: AMBER atom type → GROMACS atom type mapping:**
   - AMBER/GAFF2 uses types like: c3, c2, c, ca, cc, cd, oh, os, o, na, nh, nd, ns, nv, nf, nu, nz, hn, hc, h1, h4, ha, ho, h2
   - GROMACS ITP needs atom type NAMES for `[ atoms ]` section
   - **Key question:** Do we keep the GAFF2 type names as-is in GROMACS, or must they be mapped to OPLS-AA or other GROMACS force field types?
   - QuickIce's existing ITP files (ch4.itp, thf.itp, etoh.itp) use GAFF2-like types: c3, hc, h1, os, c5, oh, ho
   - **Conclusion from existing codebase:** QuickIce ALREADY uses GAFF2 atom type names in GROMACS! The conversion is simpler than expected.
   - But: `[ atomtypes ]` section with LJ parameters must be provided in the parent .top file or the ITP
   - Current convention in QuickIce: `[ atomtypes ]` is COMMENTED OUT in ITP, defined in main .top

6. **Parameter conversion rules:**
   - AMBER bond: k(kcal/mol/Å²) → GROMACS: kb(kJ/mol/nm²); r0(Å) → b0(nm)
     - Conversion: 1 kcal/mol = 4.184 kJ/mol; 1 Å = 0.1 nm; force constant scales as (kcal/mol/Å²) × 41840 = kJ/mol/nm²
   - AMBER angle: k(kcal/mol/rad²) → GROMACS: ctheta(kJ/mol/rad²); θ0 stays in degrees
     - Conversion: 1 kcal/mol/rad² = 4.184 kJ/mol/rad²
   - AMBER dihedral: Vn(kcal/mol) → GROMACS: kd(kJ/mol); phase(degrees) stays; pn(periodicity) stays
     - Conversion: 1 kcal/mol = 4.184 kJ/mol
   - AMBER LJ: R*(Å), ε(kcal/mol) → GROMACS: σ(nm), ε(kJ/mol)
     - σ = 2^(1/6) × R* / 10 (nm); ε = ε_AMBER × 4.184 (kJ/mol)
     - BUT: GAFF2 LJ params are in the force field itself, not in frcmod — the frcmod `NONBON` section is usually empty

7. **Dihedral handling complexities:**
   - AMBER: Multiple dihedrals for same atom quartet (different periodicities)
   - GROMACS: Multiple dihedrals for same quartet — each gets separate line with funct=9
   - AMBER "same as X-Y-Z-W, penalty score=N" comments — what do these mean?
     - These indicate which GENERAL GAFF2 parameter was used (penalty score = how far from exact match)
     - High penalty scores (>10) suggest the parameterization may be poor quality

8. **Pairs (1-4 interactions) generation:**
   - GROMACS requires explicit `[ pairs ]` section
   - AMBER doesn't have an explicit pairs section — these are implied by the exclusion rule (nrexcl=3)
   - Must enumerate all 1-4 pairs from the bond topology
   - Method: Find all (i,j) pairs where the shortest path between atoms i and j is exactly 3 bonds

9. **Impropers handling:**
   - AMBER: Impropers use wildcards (X-X-ca-ha), specific ordering matters
   - GROMACS: `[ dihedrals ]` with funct=2 (harmonic) or funct=4 (improper periodic)
   - GROMACS improper dihedrals use funct=2 with force constant and equilibrium angle
   - Need to map AMBER improper convention to GROMACS funct=2 format

10. **Coordinate unit conversion:**
    - AMBER mol2: coordinates in Ångströms
    - GROMACS .gro: coordinates in nanometers
    - Conversion: x(nm) = x(Å) / 10

### Files to Examine

- `tmp/amber_geostd/m/M00.mol2` — complex molecule with aromatic ring, amide bonds, multiple atom types
- `tmp/amber_geostd/m/M00.frcmod` — corresponding force field modifications
- `tmp/amber_geostd/t/THF.mol2` — THF (but this is NOT simple THF — it's a complex molecule with THF residue name in PDB, 55 atoms!)
- `tmp/amber_geostd/d/DIO.mol2` — 1,4-dioxane (14 atoms, simple ring — good test case)
- `quickice/data/ch4.itp` — existing GROMACS ITP for methane (GAFF2 types, Sobtop-generated)
- `quickice/data/thf.itp` — existing GROMACS ITP for THF (GAFF2 types, Sobtop-generated)
- `quickice/data/custom/etoh.itp` — existing GROMACS ITP for ethanol (GAFF2 types, Sobtop-generated)
- `quickice/data/custom/etoh.gro` — existing GROMACS GRO for single ethanol molecule
- `quickice/output/gromacs_writer.py` — existing GROMACS export code (format reference)
- `quickice/structure_generation/itp_parser.py` — existing ITP parser (defines what QuickIce expects)
- `quickice/structure_generation/gro_parser.py` — existing GRO parser (defines what QuickIce expects)

### Sources to Consult

- GROMACS 2024 reference manual, Chapter "Topology file format" — https://manual.gromacs.org/current/reference-manual/topologies/topology-file-format.html
- AMBER mol2 format spec — https://ambermd.org/FileFormats.php#mol2
- AMBER frcmod format spec — https://ambermd.org/FileFormats.php#frcmod
- GAFF2 atom type definitions — https://ambermd.org/AmberTools.php (antechamber documentation)
- Context7: Search for "GROMACS topology format" documentation

### Output Format

`FORMAT-CONVERSION.md` should include:
- Complete format mapping tables (AMBER field → GROMACS field, with unit conversions)
- Step-by-step conversion algorithm (pseudocode)
- Edge cases and ambiguous mappings
- Quality indicators (penalty scores from frcmod, missing parameters)
- Feasibility assessment (can this be fully automated? what percentage of 28,745 molecules will convert cleanly?)
- Comparison with existing QuickIce convention (GAFF2 types already in use)

`SUMMARY-B.md`: 1-paragraph verdict on feasibility + rough LOC estimate for converter

---

## Agent C: Relevance Filtering — Hydrate-Relevant Molecule Selection

**Wave:** 2 (depends on Agent A license findings + Agent B conversion feasibility)
**Output files:** `RELEVANCE-FILTER.md`, `SUMMARY-C.md`
**Estimated research time:** 30-45 min

### Key Questions

1. **Known hydrate guest molecules:** What molecules are used as hydrate guests in MD simulation literature?
   - sI hydrate guests: CH4 (methane), CO2, C2H6 (ethane), H2S, Xe
   - sII hydrate guests: THF (tetrahydrofuran), C3H8 (propane), N2, i-C4H10 (isobutane), H2
   - sH hydrate guests: neo-pentane, cyclopentane, cyclohexane, adamantane, 2,2-dimethylbutane
   - Other relevant: 1,4-dioxane, ethylene oxide, trimethylene oxide
   
2. **How many of these are in the geostd?** Scan the actual filenames for:
   - CH4, C2H6, C3H8, THF, DIO, CPN, CYC, N2, O2, CO2
   - Also check for PDB component codes: MMA (methane), ETA (ethane), PPR (propane), etc.
   - Note: THF.mol2 in geostd is NOT simple tetrahydrofuran — it's a PDB component named "THF" (a complex molecule)

3. **Key realization from examining THF.mol2:** The PDB component "THF" is NOT simple tetrahydrofuran (C4H8O). It's a larger complex molecule. The geostd molecules are PDB components, named by 3-letter PDB codes. Simple hydrate guest molecules may have different PDB codes or may not be in the PDB at all (methane, ethane, etc. are not typical PDB ligands).
   - **This is a critical finding:** The geostd is a PDB component library, not a general small molecule library. Many simple hydrate guests may be ABSENT.
   - Must systematically check which hydrate-relevant molecules actually exist in the geostd

4. **Filtering strategy for 28,745 molecules:**
   - Approach A: Name-based filtering (match known PDB codes for hydrate guests)
   - Approach B: Structure-based filtering (filter by atom count, element composition, molecular weight)
   - Approach C: Manual curation (expert-selected list of ~50-100 molecules)
   - Approach D: Use the PDB Chemical Component Dictionary (CCD) to map PDB codes → InChI/SMILES → filter by chemical class
   
5. **Recommended subset size:** How many molecules should be bundled?
   - Too many: 28,745 molecules × ~2KB each ≈ 56MB — too large for package data
   - Too few: 5-10 molecules — not enough to justify a search panel
   - Sweet spot: 50-200 molecules that are most useful for MD simulation
   - Must cover: common hydrate guests, solvents, small organics, ions

6. **Alternative sources for missing simple molecules:**
   - If methane, ethane, propane are NOT in geostd, where do we get them?
   - QuickIce already has ch4.itp and thf.itp (Sobtop-generated)
   - Can the conversion tool be used on user-supplied AMBER files as a fallback?

### Files to Examine

- Scan ALL 28,745 mol2 filenames for hydrate-relevant names
- Cross-reference with known PDB component codes for small organics
- Check `quickice/data/` for existing molecules QuickIce already ships
- Examine the geostd README for how PDB codes map to molecules

### Sources to Consult

- Sloan & Koh "Clathrate Hydrates of Natural Gases" — table of common hydrate formers
- PDB Chemical Component Dictionary — https://www.wwpdb.org/data/ccd
- Literature search: "clathrate hydrate guest molecule MD simulation"
- Wikipedia: Clathrate hydrate guest molecule lists

### Output Format

`RELEVANCE-FILTER.md` should include:
- Table of known hydrate guest molecules with PDB codes (if they exist in geostd)
- Actual scan results: how many of the target molecules exist in geostd
- Filtering strategy recommendation (which approach + why)
- Estimated final subset size
- List of molecules NOT in geostd that must come from elsewhere
- Alternative acquisition strategies for missing molecules

`SUMMARY-C.md`: 1-paragraph verdict on what subset is feasible + what's missing

---

## Agent D: Architecture & Integration Research

**Wave:** 3 (depends on Agent B conversion approach + Agent C relevance scope)
**Output files:** `ARCHITECTURE.md`
**Estimated research time:** 30-45 min

### Key Questions

1. **Where do converted molecule files live?**
   - Option A: Package data directory (`quickice/data/molecules/`) — bundled with install
   - Option B: On-demand download (fetch from server when user selects)
   - Option C: User-side cache (convert once, cache in ~/.quickice/molecules/)
   - Recommendation based on license findings (Agent A) and subset size (Agent C)

2. **How does the GUI search/browse panel integrate into existing CustomMoleculePanel?**
   - Current flow: User manually uploads .gro + .itp files
   - New flow: User can EITHER upload files OR browse/search pre-built library
   - UI changes needed in `custom_molecule_panel.py`:
     - QComboBox or search field for molecule selection
     - Preview of selected molecule (VTK or text)
     - Auto-populate .gro/.itp paths from library selection
   - How does this interact with existing `CustomMoleculeConfig` dataclass?
   - Does `custom_molecule_inserter.py` need changes? (Probably not — it already takes paths)

3. **Data model for molecule library:**
   - What metadata to store per molecule? (name, formula, MW, SMILES/InChI, category/tags, atom count, source)
   - How to index for fast search? (Python dict keyed by name? SQLite FTS5? Whoosh?)
   - How to handle atom type conflicts across molecules? (QuickIce convention: atomtypes in .top, not .itp)

4. **Conversion tool architecture:**
   - Standalone function: `amber_to_gromacs(mol2_path, frcmod_path) -> (gro_content, itp_content)`
   - Where does this live? (`quickice/converters/amber_to_gromacs.py`?)
   - What dependencies? Must be pure Python (no ACPYPE/ParmEd)
   - Must handle: mol2 parsing, frcmod parsing, unit conversion, pairs generation, GRO/ITP writing
   - Error handling: What if frcmod has missing parameters? (penalty score > threshold?)

5. **Integration with existing export pipeline:**
   - `gromacs_writer.py` already handles atom types, ITP bundling, .top generation
   - Pre-built molecules need: .gro file (single molecule coords) + .itp file (topology)
   - These feed directly into existing `CustomMoleculeInserter` workflow
   - The `[ atomtypes ]` section must be extracted and merged into the parent .top file
   - Current QuickIce convention: comment out `[ atomtypes ]` in ITP, define in .top

6. **File format for molecule library index:**
   - Option A: Python module with dict literal (simple, fast, no parsing)
   - Option B: JSON file (portable, tool-accessible)
   - Option C: YAML file (human-readable, but slow for large dicts)
   - Option D: SQLite database (fast queries, but complex setup for <200 entries)

### Files to Examine

- `quickice/gui/custom_molecule_panel.py` — existing GUI panel (1307 lines)
- `quickice/gui/custom_molecule_worker.py` — existing worker
- `quickice/structure_generation/custom_molecule_inserter.py` — existing inserter
- `quickice/structure_generation/types.py` — CustomMoleculeConfig dataclass
- `quickice/output/gromacs_writer.py` — export pipeline
- `quickice/output/export.py` — export UI integration
- `quickice/structure_generation/itp_parser.py` — ITP parser expectations

### Output Format

`ARCHITECTURE.md` should include:
- Component diagram (converter → data files → GUI panel → inserter → export)
- Data model (molecule library index schema)
- UI integration points (which widgets to add, which signals to connect)
- File organization (where new files go)
- API design for `amber_to_gromacs()` converter function
- Dependency analysis (what existing code changes, what's purely additive)

---

## Agent E: Pitfalls & Edge Cases Research

**Wave:** 3 (parallel with Agent D)
**Output files:** `PITFALLS.md`
**Estimated research time:** 20-30 min

### Key Questions

1. **Atom type name collisions:** Multiple molecules may define the same atom type name (e.g., "c3") with DIFFERENT LJ parameters. How to handle?
   - In AMBER/GAFF2: Atom types are universal — "c3" means the same thing everywhere
   - In GROMACS: Atom types can be molecule-specific or global
   - QuickIce convention: Atom types are GLOBAL (defined in .top, not per-ITP)
   - Problem: What if user combines two custom molecules with conflicting atom type definitions?
   - This is ALREADY a problem in QuickIce — not new, but must be documented

2. **Charge scaling issues:** AMBER uses different charge conventions than some GROMACS force fields.
   - GAFF2 + abcg2 charges: Are these compatible with TIP4P-ICE water model?
   - Cross-parameterization: Guest-host non-bonded interactions (Lorentz-Berthelot combining rules)
   - This is the BIGGEST scientific pitfall — incorrect LJ combining rules produce wrong hydrate stability

3. **Missing force field parameters:** frcmod files with high penalty scores indicate poor parameterization.
   - What penalty score threshold indicates "do not use"?
   - How to flag these to the user in the GUI?

4. **Molecular geometry quality:** geostd geometries are PBEh-3c optimized — but are they suitable as GROMACS starting structures?
   - GROMACS will energy-minimize anyway — so starting geometry quality may not matter much
   - BUT: Bad starting geometries (clashing atoms, unreasonable bond lengths) can cause minimization failures

5. **1-4 interaction scaling:** AMBER uses fudge factor 1/1.2 for LJ and 1/2 for electrostatics on 1-4 pairs. GROMACS can handle this via `[ defaults ]` section in .top — but only if the whole system uses the same scaling.
   - If mixing GAFF2 molecules with TIP4P-ICE water, the default nonbonded settings must be consistent
   - TIP4P-ICE uses standard Lorentz-Berthelot combining rules, no 1-4 scaling (water has no 1-4 pairs)
   - GAFF2 molecules need AMBER-style 1-4 scaling
   - This is configured in `[ defaults ]` section — but `[ defaults ]` is system-wide, not per-molecule!
   - **CRITICAL:** This is an inherent incompatibility between AMBER and GROMACS force fields

6. **GRO file for single molecules:** What box dimensions to use?
   - Option: Use 0.0 0.0 0.0 — but this may cause issues with some GROMACS tools
   - Option: Use a box large enough for the molecule + margin
   - Current QuickIce convention: `etoh.gro` uses 0.0 0.0 0.0 box

7. **Residue naming in GRO:** Pre-built molecules need a residue name in the GRO file.
   - Current convention: Single residue per molecule (resname = moleculetype name)
   - mol2 files have `@<TRIPOS>SUBSTRUCTURE` with residue info — but it's usually just one residue

8. **Atom naming in ITP:** mol2 uses unique atom names (CAA, CAI, etc. or H1, H2, etc.). GROMACS ITP needs atom names.
   - QuickIce convention: Use element-like names (C, H, O, N) with unique numbering
   - Must map mol2 atom names to GROMACS-style names? Or keep as-is?
   - Current ITP files use short names (C, H, O, CA, CB, etc.)
   - mol2 names are longer (CAA, CAI, H1, H2) — these can be kept as-is in GROMACS

### Output Format

`PITFALLS.md` should include:
- Numbered pitfalls (P1, P2, ...) with severity, description, detection, prevention, and recovery
- Severity levels: CRITICAL (data corruption/wrong science), HIGH (feature breakage), MEDIUM (poor UX), LOW (minor annoyance)
- Focus on pitfalls UNIQUE to this feature (not general GROMACS pitfalls)

---

## Agent F: Synthesis & Summary

**Wave:** 4 (depends on all prior agents)
**Output files:** `SYNTHESIS.md`, `SUMMARY.md`
**Estimated research time:** 15-20 min

### Key Questions

1. **Overall go/no-go:** Based on license research (Agent A), can this feature ship?
2. **Scope recommendation:** Based on relevance filter (Agent C), how many molecules to bundle?
3. **Technical feasibility:** Based on format conversion research (Agent B), is the converter buildable?
4. **Risk assessment:** Based on pitfalls (Agent E), what are the blocking issues?
5. **Phase recommendations:** Based on architecture (Agent D), what's the implementation sequence?

### Output Format

`SYNTHESIS.md` should include:
- Executive summary (3-5 sentences)
- Decision matrix: each key question → answer → confidence level
- Recommended feature scope (what to build, what to defer)
- Suggested phase structure for roadmap
- Open questions requiring user input
- Cross-references to detailed research files

`SUMMARY.md` should follow the existing research SUMMARY format (see complex-hydrate-atomsk/SUMMARY.md for template):
- Domain, Date, Overall confidence
- Executive Summary
- Key Findings (Stack, Architecture, Critical pitfall)
- Implications for Roadmap (phased recommendations)
- Confidence Assessment table
- Quick Wins
- Open Questions
- Gaps to Address

---

## Agent Prompt Templates

Each agent should be given a prompt following this structure:

```
You are a research agent for the QuickIce project. Research the domain of
[YOUR DOMAIN] for a "Pre-built small molecules for GROMACS" feature.

## Feature Context
Users currently must supply their own .gro/.itp files for custom molecule
insertion. The goal is to provide a library of pre-built small molecules
(converted from AMBER geostd) with a GUI search/browse panel.

## Your Task
Research [YOUR SPECIFIC QUESTIONS]. Produce [OUTPUT FILES].

## Key Sources
- [LIST SPECIFIC FILES AND URLs TO CONSULT]

## Output Format
[YOUR SPECIFIC FORMAT REQUIREMENTS]

## Constraints
- Do NOT modify any code files — this is research only
- Use GSD research conventions: confidence levels (HIGH/MEDIUM/LOW),
  source hierarchy (primary > secondary > tertiary)
- Focus on ANSWERS, not process documentation
- If you cannot find a definitive answer, state the uncertainty clearly
```

## File Output Summary

| Agent | Wave | Output Files | Key Deliverable |
|-------|------|--------------|-----------------|
| A | 1 | `LICENSE.md`, `SUMMARY-A.md` | Can we redistribute? Under what terms? |
| B | 1 | `FORMAT-CONVERSION.md`, `SUMMARY-B.md` | Conversion algorithm + feasibility |
| C | 2 | `RELEVANCE-FILTER.md`, `SUMMARY-C.md` | Which molecules to bundle + what's missing |
| D | 3 | `ARCHITECTURE.md` | Component design + integration points |
| E | 3 | `PITFALLS.md` | Numbered pitfalls with severity + prevention |
| F | 4 | `SYNTHESIS.md`, `SUMMARY.md` | Go/no-go + phased roadmap |
| | | **Total: 8 files** | |
