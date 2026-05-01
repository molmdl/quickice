# Prompt 3: Documentation Updates

**Workflow:** Direct prompt (no command needed)
**Priority:** MEDIUM
**Estimated time:** 1-2 hours

---

## Instructions

Start a new session, then paste the prompt directly.

---

## Prompt

Update documentation with the following improvements:

### 1. Clarify Phase Detection vs Generation
**File:** `docs/principles.md:52-56`

Update the Phase Mapping section to clarify:
```markdown
Phase detection identifies regions for:
- 8 generatable phases (Ih, Ic, II, III, V, VI, VII, VIII)
- 4 detectable-only phases (IX, X, XI, XV) — no GenIce2 lattices available
- Liquid water and vapor regions

Note: Proton-ordered phases (Ice XI, IX, XV) and symmetric hydrogen 
bond phase (Ice X) are detected but cannot be generated due to lack 
of GenIce2 lattice implementations.
```

### 2. Add Hydrate Lattice Type Descriptions
**File:** `docs/gui-guide.md:230-236`

Add table after lattice type mention:
```markdown
### Lattice Types

| Lattice | Description | Typical Guests | Cage Types |
|---------|-------------|----------------|------------|
| sI | Structure I | CH₄, CO₂ | 2 small + 6 large cages |
| sII | Structure II | THF, larger guests | 16 small + 8 large cages |
| sH | Structure H | Requires helper molecule | 3 small + 2 medium + 1 large |
```

### 3. Document Water Density Calculation Method
**File:** `README.md` (add to principles or methods section)

```markdown
### Water Density Calculation

Water density for interface generation uses the IAPWS-95 formulation 
for accuracy across the temperature-pressure range:

Wagner, W., & Pruß, A. (2002). The IAPWS formulation 1995 for the 
thermodynamic properties of ordinary water substance for general 
and scientific use. Journal of Physical and Chemical Reference Data, 
31(2), 387-535.
DOI: https://doi.org/10.1063/1.1461829
```

### 4. Add Ion Concentration Formula Explanation
**File:** `docs/gui-guide.md:413-418`

Add after the formula:
```markdown
**Calculation steps:**
1. Convert volume from nm³ to L (multiply by 10⁻²⁴)
2. Multiply by concentration (mol/L) to get moles of ions
3. Multiply by Avogadro's number (N_A = 6.022×10²³) to get ion pairs
4. Enforce equal Na⁺/Cl⁻ counts for charge neutrality

**Example:** For 100 nm³ box at 0.15 M:
- N_pairs = 0.15 × 100 × 10⁻²⁴ × 6.022×10²³ ≈ 9 ion pairs
```

### 5. Explain Ice II Constraint
**File:** `docs/gui-guide.md:306-311`

Add explanation:
```markdown
**Note on Ice II:** Ice II (rhombohedral) cannot form orthogonal 
supercells due to its rhombohedral crystal symmetry, which is 
incompatible with the orthogonal box requirements for interface 
generation. Other hexagonal and cubic phases can be transformed 
to orthogonal cells.
```

### 6. Add Coverage Test Command
**File:** `README.md:429-439`

Add to test commands:
```markdown
### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=quickice tests/

# Run specific test file
pytest tests/test_phase_mapping.py -v
```
```

### 7. Document Ion ITP Generation
**File:** `README.md:33-36`

Add clarification:
```markdown
**Note:** Ion .itp files are generated dynamically at export time 
using Madrid2019 force field parameters. They are not bundled as 
static files in quickice/data/.
```

---

## References

- `.planning/code_analysis/DOC_CROSSCHECK_2026-05-02.md` - Missing Documentation #19-23
- `.planning/code_analysis/DOC_CROSSCHECK_2026-05-02.md` - Major Inconsistencies #6, #10, #11

---

## Success Criteria

- [ ] Phase detection/generation capability clearly documented
- [ ] Hydrate lattice types explained with table
- [ ] Water density method documented with citation
- [ ] Ion concentration formula explained step-by-step
- [ ] Ice II constraint explained
- [ ] Coverage test command added
- [ ] Dynamic ion ITP generation noted
