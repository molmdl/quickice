# License Analysis: Pre-built Small Molecules for GROMACS

**Project:** QuickIce
**Feature:** Pre-built small molecules converted from AMBER geostd to GROMACS format
**Researched:** 2026-06-12
**Overall confidence:** MEDIUM

> **DISCLAIMER:** This is not legal advice. This analysis represents research into licensing terms and community interpretations. Consult a qualified attorney for definitive legal guidance.

---

## Provenance Chain

The geostd data files trace through this provenance chain:

```
PDB Chemical Component Dictionary (CCD)  ──CC0──┐
                                                  │
phenix geostd (geometry-optimized structures) ──BSD─┤
           [PBEh-3c QM optimization]               │
                                                  ▼
                                       gcif files (phenix format)
                                                  │
AmberTools24/antechamber ──GPL-3.0+───────────────┤
           [atom typing + charge assignment]       │
           (uses GAFF2 atom types + abcg2 charges) │
                                                  ▼
                                        mol2 + frcmod files
                                                  │
QuickIce converter ──MIT──────────────────────────┤
           [format translation only]               │
                                                  ▼
                                        .gro + .itp files (GROMACS)
```

---

## 1. PDB Chemical Component Dictionary (CCD)

**License:** CC0 1.0 Universal (Public Domain Dedication)
**What it covers:** Original molecular definitions (atom names, residue names, connectivity, coordinates) for all small molecules in the PDB
**Source:** https://www.wwpdb.org/about/usage-policies

### Redistribution Rights

**Verdict: CAN redistribute under MIT** | **Confidence: HIGH**

The wwPDB explicitly states:

> "Data files contained in the PDB archive are available under the CC0 1.0 Universal (CC0 1.0) Public Domain Dedication."

Under CC0, the data is in the public domain. No copyright restrictions apply. You may use, modify, and redistribute for any purpose without attribution requirements (though attribution is encouraged).

### Notes

- The CCD is the ultimate upstream source for molecular definitions
- phenix geostd derives its starting geometries from CCD data
- CC0 is fully compatible with MIT — no obligations imposed
- The wwPDB encourages but does not require attribution

---

## 2. phenix geostd

**License:** BSD-3-Clause (University of California / LBNL)
**What it covers:** The SOFTWARE in the repository (scripts, C code, Makefiles, restraint data)
**Source:** https://github.com/phenix-project/geostd — LICENSE.txt file

### Exact License Text (BSD-3-Clause)

```
Copyright (c) 2009, The Regents of the University of California,
through Lawrence Berkeley National Laboratory

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

(1) Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.
(2) Redistributions in binary form must reproduce the above copyright
    notice, this list of conditions and the following disclaimer in the
    documentation and/or other materials provided with the distribution.
(3) Neither the name of the University of California, Lawrence Berkeley
    National Laboratory, U.S. Dept. of Energy nor the names of its
    contributors may be used to endorse or promote products derived from
    this software without specific prior written permission.
```

### Redistribution Rights

**Verdict: CAN redistribute under MIT** | **Confidence: HIGH**

BSD-3-Clause is a permissive license fully compatible with MIT. The only requirements are:
1. Retain the copyright notice
2. Reproduce the license text and disclaimer
3. Don't use LBNL/UC names for endorsement

### Critical Detail: mol2/frcmod files ARE included in phenix geostd

The phenix geostd README explicitly states:

> "This repository also includes Amber force field files (\*.mol2, \*.frcmod) for most of the ligands. These were created using AmberTools24/antechamber, with the gaff2 and ABCG2 options."

**This is extremely significant.** The phenix geostd repository — under BSD-3-Clause — explicitly distributes mol2 and frcmod files that were created by the same antechamber/parmchk2 pipeline used for the AMBER geostd archive. This constitutes a practical precedent where a major research institution (LBNL/UC) has taken the position that antechamber output files can be distributed under a permissive license.

### Notes

- The phenix geostd repository's mol2/frcmod files are a direct precedent for redistributing antechamber output under BSD
- The geostd data (gcif restraint files) are also BSD-3-Clause
- The starting geometries come from CCD (CC0) + PBEh-3c optimization (LBNL's own work)

---

## 3. AmberTools24 (antechamber, parmchk2, sqm)

**License:** GPL-3.0-or-later AND LGPL-3.0-or-later AND BSD-3-Clause AND MIT (composite)
**What it covers:** The SOFTWARE programs — antechamber, parmchk2, sqm, and the GAFF2 force field parameter database
**Source:** https://ambermd.org/AmberTools.php, conda-forge package metadata

### The Central Legal Question: Is OUTPUT of a GPL program automatically GPL?

**FSF position (authoritative): NO.**

From the GNU GPL FAQ (https://www.gnu.org/licenses/gpl-faq.html):

#### FAQ #CanIUseGPLToolsForNF:

> "Can I use GPL-covered editors such as GNU Emacs to develop nonfree programs? Can I use GPL-covered tools such as GCC to compile them?
>
> **Yes, because the copyright on the editors and tools does not cover the code you write.** Using them does not place any restrictions, legally, on the license you use for your code."

#### FAQ #GPLOutput:

> "Is there some way that I can GPL the output people get from use of my program?
>
> **In general this is legally impossible; copyright law does not give you any say in the use of the output people make from their data using your program.** If the user uses your program to enter or convert her own data, the copyright on the output belongs to her, not you. More generally, **when a program translates its input into some other form, the copyright status of the output inherits that of the input it was generated from.**"

#### FAQ #WhatCaseIsOutputGPL:

> "In what cases is the output of a GPL program covered by the GPL too?
>
> **The output of a program is not, in general, covered by the copyright on the code of the program.** So the license of the code of the program does not apply to the output, whether you pipe it into a file, make a screenshot, screencast, or video.
>
> The exception would be when the program displays a full screen of text and/or art that **comes from the program**. Then the copyright on that text and/or art covers the output."

### The Exception: When Output Copies Code/Data FROM the Program

The FSF FAQ identifies one exception: when the program copies substantial portions of its own code or data into the output. The classic example is Bison, which copies a standard parser skeleton into its output. The FSF explicitly added an exception for Bison to allow its output to be used in non-GPL programs.

**Is antechamber analogous to Bison?** This is the key question for GAFF2 atom types and force field parameters.

### Analysis: What antechamber/parmchk2 Write to Output

Looking at the actual mol2 and frcmod output files:

**mol2 file contents** (from amber_geostd/0/000.mol2):
```
@<TRIPOS>MOLECULE
000
    8     7     1     0     0
SMALL
abcg2

@<TRIPOS>ATOM
      1 C    -0.5160  0.1030  0.0010 c    1 000  0.819100
      2 O    -0.3750  1.3330  0.0180 o    1 000 -0.729000
      3 OA    0.6310 -0.6760 -0.0190 os   1 000 -0.542100
      4 CB    1.8700 -0.0060 -0.0100 c3   1 000  0.200900
      ...
```

**frcmod file contents** (from amber_geostd/0/000.frcmod):
```
Remark line goes here
MASS
BOND
ANGLE
DIHE
IMPROPER
o -o -c -os   1.1  180.0  2.0  Same as X -o -c -o, penalty score= 49.6
NONBON
```

The mol2 file contains:
- **Coordinates** — derived from phenix geostd input (BSD-3-Clause / CC0)
- **GAFF2 atom type labels** (c, o, os, c3, h1) — short functional labels assigned by antechamber
- **abcg2 partial charges** — computed by running sqm (AM1 QM) then applying BCC corrections

The frcmod file contains:
- **Force field parameters** (bond, angle, dihedral, improper, VDW) — looked up from the GAFF2 parameter database within AmberTools

### Are GAFF2 Atom Type Labels Copyrightable?

**Verdict: Likely NOT copyrightable as individual labels** | **Confidence: MEDIUM**

GAFF2 atom type names are short functional labels (e.g., "c" for aromatic carbon, "c3" for aliphatic carbon, "o" for carbonyl oxygen, "os" for ester oxygen, "h1" for hydrogen bonded to one heavy atom). These are:

- **Too simple for copyright** — individual two-character labels lack the originality required by Feist v. Rural
- **Functional classification** — they are a naming convention for classifying atom types, which is a functional system, not creative expression
- **Merger doctrine** — there are only a limited number of ways to name these atom types; the idea merges with the expression

### Are GAFF2 Force Field Parameters Copyrightable?

**Verdict: Debatable — likely NOT copyrightable as scientific facts, but collection copyright is arguable** | **Confidence: MEDIUM-LOW**

Force field parameters (bond lengths, force constants, angle values, dihedral barriers, VDW radii and well depths) are:

- **Scientific measurements/derivations** — they approximate physical reality (how atoms interact)
- **Determined by fitting procedures** — the specific values come from fitting to quantum mechanical data
- **NOT creative expression** — they represent the best available fit, not artistic choice

Under US copyright law (Feist v. Rural Publications, 499 U.S. 340 (1991)):
- Facts are NOT copyrightable
- A collection of facts may receive "thin" copyright protection for the creative selection/arrangement
- But the individual data points remain uncopyrightable

The GAFF2 force field is a curated collection of parameters. The SELECTION of which parameters to include and how to organize them could arguably receive thin copyright protection as a compilation. However, the individual parameter values themselves are scientific facts.

**For the frcmod output specifically:** The frcmod file contains a SUBSET of GAFF2 parameters relevant to one molecule. This is not copying the creative arrangement of the full force field — it's extracting relevant individual data points. Under Feist, individual data points are not copyrightable even if the collection has thin copyright.

### Are abcg2 Charges "Output" or "Copying"?

The abcg2 charge model works in two steps:
1. Run AM1 semi-empirical QM calculation (via `sqm`) → produces raw AM1 charges
2. Apply Bond Charge Corrections (BCC) from a parameter table stored in AmberTools

The resulting charges in the mol2 file are **computed values** — they are NOT verbatim copies of the BCC parameter table. The BCC parameters are used as inputs to a mathematical formula, not copied directly into the output. This is analogous to a compiler using optimization flags — the optimization parameters influence the output but are not reproduced in it.

**Verdict: Charges are OUTPUT of the program, not copies of its data** | **Confidence: HIGH**

### Overall AmberTools Verdict

**Verdict: Output files (mol2/frcmod) from antechamber/parmchk2 are NOT automatically GPL** | **Confidence: MEDIUM**

Reasoning:
1. The FSF FAQ explicitly states GPL does not cover program output (HIGH confidence)
2. The output inherits the license of the input (CC0/BSD-3-Clause from phenix geostd) (HIGH confidence)
3. GAFF2 atom type labels are likely not copyrightable (MEDIUM confidence)
4. Individual force field parameters are likely not copyrightable as scientific facts (MEDIUM-LOW confidence)
5. The phenix geostd repository provides practical precedent for distributing antechamber output under BSD-3-Clause (HIGH confidence for precedent, MEDIUM for legal weight)
6. The abcg2 charges are computed output, not copied data (HIGH confidence)

### Mitigating Factor: No GPL "infection" for data

Even if some portion of the output were deemed to contain AmberTools-copyrightable material, the practical precedent from phenix geostd and the scientific nature of the data strongly suggest the AMBER team does not consider these output files to be GPL-encumbered. The AMBER team distributes the geostd archive without any GPL license notice on the data files, which further supports the interpretation that these are not GPL derivative works.

---

## 4. AMBER geostd Data Archive (amber_geostd.tar.bz2)

**License:** NO EXPLICIT LICENSE on data files
**What it covers:** 28,745 mol2 + frcmod files distributed from https://ambermd.org/downloads/amber_geostd.tar.bz2
**Source:** The archive itself contains only a README (no LICENSE file)

### The Problem

The amber_geostd.tar.bz2 archive contains no LICENSE or COPYING file. The README describes the methodology but does not state the licensing terms for the data files.

Under copyright law, the default when no license is specified is "all rights reserved." However:

1. The data is freely downloadable from a public website — this implies at least a license to download and use
2. The AMBER team distributes this as a convenience for AMBER users
3. The README does not impose any license terms on the data
4. No GPL license notice appears in the archive

### Redistribution Rights

**Verdict: CANNOT confidently redistribute under MIT without clarification** | **Confidence: MEDIUM**

The absence of an explicit license creates legal ambiguity. While there are strong arguments that the data files are OUTPUT of the software (and thus not GPL-encumbered), the lack of any license statement means there is no clear grant of redistribution rights.

### Viable Workarounds

1. **Use phenix geostd as the source instead** — The phenix geostd repository contains equivalent mol2/frcmod files under an explicit BSD-3-Clause license. This eliminates the ambiguity.
2. **Contact the AMBER team** — Request explicit permission to redistribute the data under MIT or BSD terms.
3. **Converter-only approach** — Don't bundle pre-built data at all; ship only the conversion tool.

---

## 5. GAFF2 Force Field (Atom Types + Parameters)

**License:** Part of AmberTools (GPL-3.0-or-later)
**What it covers:** The force field parameter database files (gaff2.dat, etc.) within the AmberTools installation
**Source:** Distributed within AmberTools source

### Copyrightability Analysis

**Individual parameters: NOT copyrightable** | **Confidence: MEDIUM-LOW**

Under Feist v. Rural, individual facts (bond lengths, force constants, VDW parameters) are not copyrightable. The specific numerical values represent scientific approximations of physical reality, arrived at through fitting procedures. They are discovered, not created.

**Force field as a compilation: ARGUABLY copyrightable** | **Confidence: MEDIUM-LOW**

The selection and organization of GAFF2 parameters into a complete force field could receive thin copyright protection for creative arrangement. However:
- The GAFF2 force field covers "many organic molecules" — it aims for comprehensive coverage, which is not a creative selection
- The arrangement follows standard force field conventions (atoms → bonds → angles → dihedrals → impropers → nonbonded)
- This is a standard, functional organization, not a creative one

**Atom type naming convention: NOT copyrightable** | **Confidence: MEDIUM**

The naming scheme (c, c1, c2, c3, ca, cb, cc, cd, ck, cm, cn, cq, cx, c5... for carbon types) is a functional classification system. Under Baker v. Selden (101 U.S. 99 (1879)), the expression of a functional system merges with the idea when there are only limited ways to express it.

### Redistribution Verdict for GAFF2 Parameters

**Verdict: Individual parameters used in frcmod files are likely redistributable** | **Confidence: MEDIUM-LOW**

The frcmod file is NOT a copy of the GAFF2 force field database. It is a subset of individual parameters relevant to one specific molecule. Individual scientific data points are not copyrightable. The thin copyright on the compilation (if any) does not extend to individual data points extracted from it.

### Risk Assessment

| Risk | Severity | Likelihood |
|------|----------|------------|
| AMBER team claims GPL on force field data | High | Low — no precedent, contradicts scientific norms |
| Court finds force field parameters copyrightable | High | Low — Feist precedent, scientific data |
| Court finds compilation copyright extends to subsets | Medium | Low-Medium — no clear precedent for parameter subsets |

---

## 6. abcg2 Charge Method

**License:** The BCC parameter table is part of AmberTools (GPL-3.0-or-later)
**What it covers:** The bond charge correction parameters used to convert AM1 charges to abcg2 charges
**Source:** Distributed within AmberTools source

### Are abcg2 Charges Derivative of AmberTools?

The abcg2 charge assignment process:
1. `antechamber` calls `sqm` to perform AM1 semi-empirical QM calculation
2. The AM1 calculation produces raw partial charges
3. BCC parameters are applied to correct these charges
4. The resulting abcg2 charges are written to the mol2 file

The charges in the mol2 file are **computed output**, not copies of the BCC parameter table. The BCC parameters influence the result mathematically but are not reproduced in the output. This is analogous to:
- A calculator using stored constants (pi, e) — the result is output, not a copy of the constants
- A compiler applying optimization passes — the optimized code is output, not a copy of the optimizer

**Verdict: abcg2 charges are OUTPUT of AmberTools, not derivative works** | **Confidence: HIGH**

---

## 7. Converted .gro/.itp Files (GROMACS Format)

**License:** Depends on input data license
**What it covers:** GROMACS topology and coordinate files produced by QuickIce's converter

### Format Translation and Copyright

Under the FSF FAQ, "when a program translates its input into some other form, the copyright status of the output inherits that of the input it was generated from."

The QuickIce converter performs a format translation:
- mol2 (AMBER coordinates + atom types + charges) → .gro (GROMACS coordinates)
- frcmod (AMBER parameters) → .itp (GROMACS topology)

The converter itself is MIT-licensed QuickIce code. The output inherits the license of the input data:
- If input is from phenix geostd → BSD-3-Clause → MIT-compatible
- If input is from PDB CCD → CC0 → no restrictions
- If input is from AMBER geostd → ambiguous → RISK

**Verdict: Converted files inherit the license of their source data** | **Confidence: HIGH**

---

## Summary Verdict Table

| Component | License | Redistribute under MIT? | Confidence |
|-----------|---------|--------------------------|------------|
| PDB CCD | CC0 1.0 | **CAN** — public domain | HIGH |
| phenix geostd (software) | BSD-3-Clause | **CAN** — permissive | HIGH |
| phenix geostd (mol2/frcmod data) | BSD-3-Clause | **CAN** — permissive | HIGH |
| AmberTools (software code) | GPL-3.0+ | N/A — not distributing software | HIGH |
| AmberTools OUTPUT (mol2/frcmod) | Inherits input license | **CAN** — FSF FAQ + precedent | MEDIUM |
| AMBER geostd archive (data) | No explicit license | **RISKY** — no clear grant | MEDIUM |
| GAFF2 atom type labels | Likely not copyrightable | **CAN** — functional labels | MEDIUM |
| GAFF2 parameters (individual) | Likely not copyrightable | **CAN** — scientific facts | MEDIUM-LOW |
| GAFF2 compilation | Arguable thin copyright | **RISKY** — debatable | LOW |
| abcg2 charges | Output of program | **CAN** — computed, not copied | HIGH |
| Converted .gro/.itp | Inherits input | **CAN** if input is BSD-3/CC0 | HIGH |

---

## Viable Redistribution Strategies

### Strategy A: Converter-Only Tool (SAFEST)

- Ship only the format converter (MIT)
- Users must obtain mol2/frcmod files themselves
- Sources: download phenix geostd (BSD-3) or run AmberTools
- **License risk: NONE**
- **User experience: POOR** — requires AmberTools installation, multi-step process

### Strategy B: Bundle phenix geostd Data (RECOMMENDED)

- Ship mol2/frcmod files from the phenix geostd repository (BSD-3-Clause)
- These are the same antechamber output, explicitly under BSD-3
- Ship converter (MIT) for mol2/frcmod → .gro/.itp
- **License risk: VERY LOW** — explicit BSD-3-Clause with attribution
- **User experience: GOOD** — pre-built molecules available immediately

Implementation:
1. Include phenix geostd mol2/frcmod files with BSD-3-Clause attribution
2. QuickIce converter translates these to GROMACS format at install time or on-demand
3. User runs QuickIce with bundled data — no AmberTools needed

### Strategy C: Bundle AMBER geostd Data (HIGHER RISK)

- Ship mol2/frcmod from amber_geostd.tar.bz2
- No explicit license — legal ambiguity
- **License risk: MEDIUM** — implied license but no explicit grant
- **User experience: BEST** — largest coverage (28,745 molecules)

Mitigations:
- Contact AMBER team for explicit redistribution permission
- If permission obtained, redistribute with appropriate attribution

### Strategy D: Re-derive from PDB CCD (CREATIVE)

- Download CCD data (CC0) directly
- Write a standalone tool that assigns GAFF2-like atom types and generates charges
- Does NOT use AmberTools — uses independently implemented algorithms
- **License risk: NONE** (CC0 input + original code)
- **User experience: VARIABLE** — quality depends on reimplementation
- **Effort: VERY HIGH** — essentially re-implementing antechamber

### Strategy E: Hybrid (PRACTICAL)

- Bundle phenix geostd mol2/frcmod under BSD-3-Clause (Strategy B)
- Provide a user-facing converter for additional molecules not in geostd
- For the converter, require AmberTools OR accept user-supplied mol2/frcmod
- **License risk: VERY LOW**
- **User experience: GOOD** — most molecules pre-built, others via converter

---

## Attribution Requirements

If redistributing phenix geostd data under BSD-3-Clause, the following attributions are required:

1. **phenix geostd / LBNL:**
   ```
   Copyright (c) 2009, The Regents of the University of California,
   through Lawrence Berkeley National Laboratory.
   See LICENSE-geostd.txt for full terms.
   ```

2. **GAFF2 / AmberTools (scientific credit, not legal requirement):**
   ```
   Atom types and force field parameters based on GAFF2 (v2.20):
   Wang et al., J. Comput. Chem., 2004, 25, 1157-1174
   Wang et al., J. Mol. Graphics Model., 2006, 25, 247-260
   ```

3. **abcg2 charges (scientific credit):**
   ```
   Charges assigned using the abcg2 procedure:
   He et al., J. Chem. Phys., 2020, 153, 114502
   Sun et al., J Comput Chem, 2023, 44, 1334-1346
   ```

4. **phenix geostd geometries:**
   ```
   Starting geometries from the phenix geostd database:
   Grimme et al., J. Chem. Phys. 143, 054107 (2015)
   ```

---

## Sources Consulted

| Source | URL | Confidence |
|--------|-----|------------|
| GNU GPL FAQ — Output | https://www.gnu.org/licenses/gpl-faq.html#GPLOutput | HIGH (FSF official) |
| GNU GPL FAQ — Tools | https://www.gnu.org/licenses/gpl-faq.html#CanIUseGPLToolsForNF | HIGH (FSF official) |
| GNU GPL FAQ — When output is GPL | https://www.gnu.org/licenses/gpl-faq.html#WhatCaseIsOutputGPL | HIGH (FSF official) |
| wwPDB Usage Policies | https://www.wwpdb.org/about/usage-policies | HIGH (official) |
| phenix geostd LICENSE.txt | https://github.com/phenix-project/geostd/blob/master/LICENSE.txt | HIGH (official) |
| phenix geostd README | https://github.com/phenix-project/geostd/blob/master/README.md | HIGH (official) |
| AmberTools main page | https://ambermd.org/AmberTools.php | HIGH (official) |
| conda-forge AmberTools metadata | https://anaconda.org/conda-forge/ambertools | HIGH (package metadata) |
| AMBER geostd README | Local: tmp/amber_geostd/README | HIGH (primary source) |
| Feist v. Rural | 499 U.S. 340 (1991) | HIGH (SCOTUS precedent) |
