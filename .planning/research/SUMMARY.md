# QuickIce Research Summary

**Project:** ML-based Ice Structure Generation  
**Synthesized:** 2026-03-26  
**Confidence:** HIGH (Stack, Architecture), MEDIUM-HIGH (Features, Pitfalls)

---

## Executive Summary

QuickIce is a CLI tool for generating ranked ice structure candidates from temperature (T) and pressure (P) conditions. The recommended approach uses a **rule-based phase mapper + GenIce generator** pipeline for MVP, with ML enhancements added post-baseline. The architecture follows a sequential pipeline pattern: input validation → phase mapping → coordinate generation → ranking → PDB output.

**Critical insight:** Pure ML generation fails ice rule constraints (exactly 4 hydrogen bonds per molecule). The hybrid approach—ML for phase/condition prediction, GenIce for valid coordinate generation—is essential. MVP should skip ML entirely and use rule-based T,P mapping.

Three critical pitfalls must be avoided:
1. **Ice rule violations** — enforce via GenIce, never pure ML
2. **Phase ordering confusion** — use GenIce's known phase templates
3. **Density mismatches** — include density as explicit feature

---

## Key Findings

### From STACK.md

| Technology | Version | Purpose |
|------------|---------|---------|
| NumPy | 2.4.x | Array computing, coordinate operations |
| SciPy | 1.17.x | Distance calculations, geometry |
| spglib-python | 2.7.x | Crystal symmetry validation |
| Click | 8.3.x | CLI framework |
| GenIce | 2.x | Ice structure coordinate generation |
| networkx | 3.x | Hydrogen bond network analysis |

**Key pattern:** Use PyTorch only if neural network training required. For inference, NumPy suffices.

### From FEATURES.md

**MVP Features (P1):**
- CLI with --temperature, --pressure, --nmolecules flags
- Rule-based T,P → phase mapping
- GenIce integration for valid coordinate generation
- Energy-based ranking
- Top 10 PDB output with CRYST1 records
- Basic validation (no overlap, valid space group)

**Post-MVP (P2):**
- ML-based phase prediction
- Phase identification
- Confidence scoring

**Differentiators (v2+):**
- MLIP-based relaxation (MACE/UMA)
- Sub-minute generation
- Free energy at T,P

### From ARCHITECTURE.md

**Pipeline Flow:**
```
CLI Args → Validator → Phase Mapper → GenIce → Ranker → PDB Writer
```

**Recommended Structure:**
```
src/
├── cli.py              # Click CLI entry point
├── validator.py        # Input validation
├── mapper.py           # T,P → phase mapping
├── generator.py        # GenIce wrapper
├── ranker.py           # Candidate ranking
├── writer.py           # PDB output
└── data/
    └── phases.yaml     # Phase diagram data
```

**Scaling:** Parallelize GenIce calls for >5 candidates; vectorize ranking with NumPy for >50 candidates.

### From PITFALLS.md

**Critical Pitfalls:**
1. **Ice rule violations** — ML generates invalid H-bond topology. Use GenIce only.
2. **Phase ordering confusion** — Ordered/disordered pairs (Ih/XI, III/IX) confused in databases. Use GenIce templates.
3. **Density mismatches** — ML defaults to mean density. Explicit density feature required.

**Integration Gotchas:**
- GenIce: Use public API only, never internal attributes
- PDB writing: Must include CRYST1 record with unit cell
- spglib: Pass correct cell format (lattice, positions, numbers)

---

## Implications for Roadmap

### Suggested Phase Structure

**Phase 1: Core Pipeline (MVP)**
- Rationale: Establishes validated pipeline with known-good outputs
- Delivers: CLI, validator, phase mapper, GenIce wrapper, ranker, PDB writer
- Features: All P1 from FEATURES.md
- Pitfalls to avoid: Ice rule violations (use GenIce), invalid PDB (add CRYST1)

**Phase 2: ML Enhancement**
- Rationale: Baseline must exist before ML enhancement; rule-based mapping is accurate for known phases
- Delivers: ML-based phase prediction, confidence scoring
- Features: P2 from FEATURES.md
- Pitfalls to avoid: Complex ML for simple lookup (not needed for known phases)

**Phase 3: Scale & Performance**
- Rationale: Optimize after core works; profile first
- Delivers: Parallel generation, vectorized ranking, GPU acceleration option
- Features: P3 from FEATURES.md
- Pitfalls to avoid: Premature optimization of sequential GenIce calls

### Research Flags

| Phase | Research Needs | Standard Patterns |
|-------|----------------|-------------------|
| Phase 1 | None | Pipeline architecture well-documented |
| Phase 2 | ML model selection | Need deeper research on MACE/UMA integration |
| Phase 3 | GPU profiling | Standard optimization, no research needed |

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Standard scientific Python stack, well-documented versions |
| Features | MEDIUM-HIGH | Clear MVP scope, ML enhancement is speculative |
| Architecture | HIGH | Pipeline pattern standard, component responsibilities clear |
| Pitfalls | HIGH | Critical pitfalls well-identified, recovery strategies defined |

**Gaps to Address:**
- ML model selection for Phase 2 needs deeper investigation
- GenIce API version compatibility with spglib not explicitly verified
- Performance benchmarks for scaling thresholds not available

---

## Sources

- NumPy 2.4.0 Release Notes
- SciPy 1.17.0 Documentation  
- Spglib GitHub v2.7.0
- Click Documentation v8.3.1
- GenIce2 GitHub
- Ice Phase Diagram literature
- ML crystal generation best practices

---

*Research synthesized for QuickIce project roadmap*