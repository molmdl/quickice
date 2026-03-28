# Phase 7: Audit & Correctness - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Audit codebase and documentation for consistency, scientific correctness, efficiency, safety, and citations. Issues identified are documented for fixing.

</domain>

<decisions>
## Implementation Decisions

### Citation Audit
- Trace GenIce2, IAPWS, spglib repositories/PyPI to find correct citations
- Verify citations in README.md Reference section (currently placeholder/incomplete)
- Verify all citations in docs/principles.md (GenIce2, IAPWS R14-08, ice phase diagram sources)
- Verify all citations in docs/ranking.md methodology section
- Add proper project URLs + citation notes to README
- In docs/principles.md: expand references with verified DOIs/links
- Verify: Wagner et al., Lobban et al., Salzmann et al. papers are correct sources
- Check if additional libraries need citations (spglib, iapws package)

### Documentation Consistency Audit
- Verify all CLI flags in code match documentation (docs/cli-reference.md)
- Verify actual output format matches documented examples in README
- Check all docs/ files for completeness and accuracy
- Verify help text matches docs

### Scientific Correctness Audit
- Verify phase boundary functions (melting_curves.py, solid_boundaries.py) against literature
- Verify ranking formulas (energy, density, diversity) are implemented correctly
- Verify O-O distance calculation in energy scoring
- Verify density calculation matches expected ice phase densities
- Verify units are consistent throughout (K, MPa, nm)
- Verify GenIce2 integration is correct (lattice parameters, hydrogen ordering)
- Full audit of physics formulas and implementations

### Issue Handling
- Document all audit findings in a report
- Categorize issues by severity
- Don't fix during audit phase - create documentation for future work

</decisions>

<specifics>
## Specific Ideas

- README Reference section (lines 234-238) needs proper citations with URLs
- docs/principles.md References section (lines 176-198) needs verification
- docs/ranking.md has no explicit citations but methodology should be checked
- Need to trace: https://github.com/vitroid/GenIce for GenIce2 citation
- Need to verify: IAPWS R14-08 document link is correct
- Need to find: spglib citation (space group validation library)
- Need to verify: ice phase boundary sources (Wagner, Lobban, Salzmann papers)

</specifics>

<deferred>
## Deferred Ideas

None - all areas discussed are within Phase 7 scope

</deferred>

---

*Phase: 07-audit-correctness*
*Context gathered: 2026-03-28*
