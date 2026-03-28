# Phase 7: Audit Codebase, Documentation, Scientific Correctness, Safety & Citations - Research

**Researched:** 2026-03-28
**Domain:** Scientific code auditing practices, citation verification, Python code quality
**Confidence:** HIGH

## Summary

This phase requires auditing the QuickIce codebase for code consistency, scientific correctness, efficiency, safety, and proper citations. Research confirms that auditing scientific code requires a multi-faceted approach: verifying dependencies have correct citations, validating physics implementations against authoritative sources, checking code patterns for consistency, and ensuring safety mechanisms are in place.

**Primary recommendation:** Implement a structured audit with separate checklists for citations, scientific correctness, code consistency, and safety. Document all findings in a report categorized by severity (critical/major/minor), but do not fix issues during the audit phase.

## Standard Stack

### Audit Tools and Approaches

| Tool/Approach | Purpose | Why Standard |
|---------------|---------|--------------|
| Manual code review | Verify implementation against documentation | Required for scientific code - automated tools insufficient |
| Citation tracing | Verify references point to correct sources | Essential for scientific reproducibility |
| Unit testing | Validate physics calculations | pytest for Python scientific code |
| Type checking | mypy for type consistency | Industry standard for Python |
| Documentation validation | Check CLI flags, examples, help text | Prevents user confusion |

### Supporting Tools
| Tool | Purpose | When to Use |
|------|---------|-------------|
| pytest | Run existing test suite | Verify nothing broke |
| mypy | Type annotation checking | Verify type consistency |
| pylint/ruff | Code style | Check PEP 8 compliance |

## Architecture Patterns

### Recommended Audit Structure

```
Audit Phase (Phase 7)
├── Citation Audit
│   ├── Verify GenIce2 citation (GitHub, paper)
│   ├── Verify IAPWS R14-08 citation (official URL)
│   ├── Verify spglib citation (paper, DOI)
│   └── Verify ice phase literature references
├── Documentation Consistency Audit
│   ├── CLI flags match docs
│   ├── Output format matches README examples
│   └── Help text matches documentation
├── Scientific Correctness Audit
│   ├── Phase boundary functions validated
│   ├── Ranking formulas implemented correctly
│   ├── Units consistent throughout
│   └── GenIce2 integration verified
├── Code Consistency Audit
│   ├── Naming conventions
│   ├── Error handling patterns
│   └── Module exports verified
└── Safety Audit
    ├── Input validation
    ├── File handling safety
    └── Error messages helpful
```

### Audit Report Format

Each audit finding should include:
- **Issue ID:** Sequential number (AUDIT-001, AUDIT-002, etc.)
- **Category:** citation/docs/scientific/consistency/safety
- **Severity:** critical/major/minor
- **Location:** File and line number
- **Description:** What the issue is
- **Evidence:** Why it's an issue
- **Recommendation:** How to fix

## Don't Hand-Roll

Problems that have existing solutions but need verification:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Citation verification | Guess at citations | Trace to official sources | Scientific integrity |
| Phase boundary validation | Implement from scratch | Use IAPWS R14-08 equations | Already validated |
| Ice structure generation | Custom implementation | GenIce2 | Established, tested |
| Space group validation | Custom algorithm | spglib | Robust, maintained |

## Common Pitfalls

### Citation Pitfalls

1. **Outdated repository URLs:** GenIce moved from vitroid/GenIce to genice-dev/GenIce2
   - **How to avoid:** Verify current URL in README or PyPI
   - **Warning signs:** 404 errors, stale documentation

2. **Missing DOIs:** References without persistent identifiers
   - **How to avoid:** Find DOIs for all cited papers
   - **Warning signs:** Broken links, no DOI listed

3. **Incorrect paper attribution:** Citing wrong publication
   - **How to avoid:** Verify against official project pages
   - **Warning signs:** Generic citations without specific papers

### Scientific Correctness Pitfalls

1. **Unit inconsistencies:** Mixing K and °C, MPa and GPa
   - **How to avoid:** Explicit unit annotations in code, consistent unit tests
   - **Warning signs:** Unexpected values, wrong phase selection

2. **Incorrect formulas:** Typing errors in melting curve equations
   - **How to avoid:** Compare against IAPWS R14-08 source document
   - **Warning signs:** Phase boundaries significantly different from literature

3. **Wrong cutoff values:** O-O distance cutoff too large/small
   - **How to avoid:** Use physically meaningful values (0.35 nm is standard for H-bonds)
   - **Warning signs:** Energy scores extremely high/low

### Code Consistency Pitfalls

1. **Inconsistent naming:** Mixed snake_case/camelCase
   - **How to avoid:** Follow PEP 8, document naming convention
   - **Warning signs:** Multiple styles in same module

2. **Missing error handling:** Functions that fail silently
   - **How to avoid:** Raise appropriate exceptions with messages
   - **Warning signs:** None, only detectable through testing

3. **Undocumented assumptions:** Code that relies on implicit behavior
   - **How to avoid:** Add docstrings, type hints, comments
   - **Warning signs:** Complex code without explanation

### Safety Pitfalls

1. **No input validation:** Accepting any user input
   - **How to avoid:** Validate temperature, pressure, molecule count ranges
   - **Warning signs:** Crashes on invalid input

2. **Path injection:** Not sanitizing output directory names
   - **How to avoid:** Use safe path construction, warn on traversal
   - **Warning signs:** Using user input directly in paths

3. **Silent failures:** Errors that don't inform user
   - **How to avoid:** Clear error messages, exit codes
   - **Warning signs:** User doesn't know what went wrong

## Code Examples

### Verified Citation Sources

#### GenIce2
- **Repository:** https://github.com/genice-dev/GenIce2
- **Citation:** "GenIce: Hydrogen-disordered ice structures by combinatorial generation", J. Comput. Chem. 2018
- **Paper DOI:** https://doi.org/10.1002/jcc.25179
- **CITATION.cff:** Present in repository

#### IAPWS R14-08
- **Document:** https://www.iapws.org/relguide/MeltSub.html
- **Title:** "Revised Release on the Pressure along the Melting and Sublimation Curves of Ordinary Water Substance"
- **Release date:** 2011 (revised 2018)
- **DOI:** https://doi.org/10.1063/1.3657937 (associated paper)

#### spglib
- **Repository:** https://github.com/atztogo/spglib
- **Citation:** "Spglib: a software library for crystal symmetry search", Sci. Technol. Adv. Mater., Meth. 4, 2384822 (2024)
- **DOI:** https://doi.org/10.1080/27660400.2024.2384822
- **CITATION.cff:** Present in repository

### IAPWS Melting Curve Verification (from melting_curves.py)

The IAPWS R14-08 equations in the code should match:

- **Ice Ih:** Uses triple-point parameters (Tt=273.16K, Pt=0.000611657 MPa) with specific coefficients
- **Ice III:** Range 251.165K < T ≤ 256.164K, P = 208.566 MPa at Tref
- **Ice V:** Range 256.164K < T ≤ 273.31K, P = 350.100 MPa at Tref
- **Ice VI:** Range 273.31K < T ≤ 355K, P = 632.400 MPa at Tref
- **Ice VII:** Range 355K < T ≤ 715K, exponential form

### O-O Distance Calculation (from scorer.py)

Verified physical constants:
- **Ideal O-O distance:** 0.276 nm (typical hydrogen bond length in ice)
- **Cutoff:** 0.35 nm (standard for H-bond detection)
- **Formula:** mean(|d_OO - 0.276|) × 100

### Density Calculation (from scorer.py)

Verified formula:
```
actual_density = (n_molecules × 18.01528 g/mol) / (N_A × volume_cm³)
```
Where volume conversion: 1 nm³ = 1e-21 cm³

## Specific Verification Checklist

### Citation Audit Checklist

- [ ] README.md Reference section (lines 234-238) has proper citations
- [ ] docs/principles.md GenIce2 citation points to https://github.com/genice-dev/GenIce2
- [ ] docs/principles.md IAPWS R14-08 citation has correct URL
- [ ] docs/principles.md Wagner et al. paper is correctly attributed
- [ ] docs/principles.md Lobban et al. paper is correctly attributed
- [ ] docs/principles.md Salzmann et al. paper is correctly attributed
- [ ] spglib citation added if used for validation
- [ ] All citations have DOIs or persistent URLs

### Documentation Consistency Checklist

- [ ] CLI flag --temperature matches docs (0-500K range)
- [ ] CLI flag --pressure matches docs (0-10000 MPa)
- [ ] CLI flag --nmolecules matches docs (4-100000)
- [ ] CLI flag --output documented
- [ ] CLI flag --no-diagram documented
- [ ] CLI flag --version documented
- [ ] Exit codes in cli-reference.md match actual implementation
- [ ] README output example matches actual output format

### Scientific Correctness Checklist

- [ ] Ice Ih melting curve matches IAPWS R14-08 equation
- [ ] Ice III melting curve matches IAPWS R14-08 equation
- [ ] Ice V melting curve matches IAPWS R14-08 equation
- [ ] Ice VI melting curve matches IAPWS R14-08 equation
- [ ] Ice VII melting curve matches IAPWS R14-08 equation
- [ ] O-O distance calculation uses correct cutoff (0.35 nm)
- [ ] O-O distance uses correct ideal value (0.276 nm)
- [ ] Density calculation uses correct formula
- [ ] Unit conversions are correct (nm³ to cm³)
- [ ] Phase mapping covers all 12 phases plus liquid

### Code Consistency Checklist

- [ ] All modules follow consistent naming (snake_case)
- [ ] Error messages are consistent in format
- [ ] All public functions have docstrings
- [ ] Type hints present on function signatures
- [ ] Module-level __all__ exports defined
- [ ] No deprecated imports or functions

### Safety Checklist

- [ ] Temperature validation: 0-500 K
- [ ] Pressure validation: 0-10000 MPa
- [ ] Molecule count validation: 4-100000
- [ ] Invalid inputs produce helpful error messages
- [ ] Output directory handling is safe (no path traversal)
- [ ] File write failures handled gracefully
- [ ] Exit codes are correct (1=validation, 2=mapping, 3=generation)

## State of the Art

### Citation Management for Scientific Software

Current best practices emphasize:
- CFF (CITATION.cff) files in repositories for automated citation generation
- DOIs for all published papers
- URLs that persist (not direct links to latest master)
- Credit to all dependencies, not just primary libraries

### Scientific Code Auditing

Industry moves toward:
- Reproducible research standards (computational notebooks)
- Automated testing with known validation cases
- Documentation that includes theory and limitations
- Clear separation of heuristic vs. rigorous methods

## Open Questions

1. **Citation completeness:** Are there additional libraries that should be cited (e.g., numpy, scipy, matplotlib)?
   - What we know: Major dependencies typically cited in README
   - What's unclear: Whether to cite every transitive dependency
   - Recommendation: Cite direct scientific dependencies (GenIce2, IAPWS, spglib), mention standard scientific Python stack

2. **Phase boundary accuracy:** Solid-solid boundaries use linear interpolation - is this acceptable?
   - What we know: IAPWS only covers melting curves, not solid-solid transitions
   - What's unclear: How accurate are the triple point values used?
   - Recommendation: Document as "medium confidence" in audit report

3. **Ice IV inclusion:** Code mentions Ice IV but phase mapping doesn't include it - intentional?
   - What we know: docs/principles.md lists Ice IV, but lookup.py may not support it
   - What's unclear: Whether this is intentional omission or oversight
   - Recommendation: Verify and document in audit findings

## Sources

### Primary (HIGH confidence)
- https://github.com/genice-dev/GenIce2 - Official GenIce2 repository with CITATION.cff
- https://www.iapws.org/relguide/MeltSub.html - Official IAPWS R14-08 document
- https://github.com/atztogo/spglib - Official spglib repository with citation info
- quickice/quickice/phase_mapping/melting_curves.py - Verified IAPWS implementation
- quickice/quickice/ranking/scorer.py - Verified physics formulas

### Secondary (MEDIUM confidence)
- IAPWS R14-08 associated paper: https://doi.org/10.1063/1.3657937
- GenIce J. Comput. Chem. 2018 paper reference
- spglib Sci. Technol. Adv. Mater. Meth. 2024 paper

### Tertiary (LOW confidence)
- Community discussions on ice phase boundaries (need verification)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified tools and approaches
- Architecture: HIGH - Based on established scientific code practices
- Pitfalls: HIGH - Common issues in scientific software
- Citations: HIGH - Verified against official sources

**Research date:** 2026-03-28
**Valid until:** 2026-06-28 (90 days for stable, citations unlikely to change)