# Architecture Research

**Domain:** ML-based ice structure generation
**Researched:** 2026-03-26
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Interface                        │
│                   (Temperature, Pressure, N)                │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────┐  │
│  │  T Parser   │  │  P Parser   │  │  N Calculator     │  │
│  └──────┬──────┘  └──────┬──────┘  └─────────┬─────────┘  │
├─────────┴────────────────┴──────────────────┴──────────────┤
│                   Condition Validator                       │
├─────────────────────────────────────────────────────────────┤
│                   Phase Mapper (T,P → phases)              │
├─────────────────────────────────────────────────────────────┤
│                   GenIce Integration                       │
├─────────────────────────────────────────────────────────────┤
│                   Ranking & Selection                      │
├─────────────────────────────────────────────────────────────┤
│                   PDB Output Writer                        │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| CLI Interface | Parse args, coordinate flow | Click decorators |
| Condition Validator | Validate T,P,N ranges | Simple range checks |
| Phase Mapper | Map T,P to ice phases | Rule-based lookup |
| GenIce Wrapper | Generate coordinates | GenIce API wrapper |
| Ranker | Score and sort candidates | Energy/density scoring |
| PDB Writer | Format and save output | Standard PDB format |

## Recommended Project Structure

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

### Structure Rationale

- **cli.py:** Single entry point, keeps CLI logic centralized
- **validator.py:** Separated validation for testability
- **mapper.py:** Isolated phase mapping logic
- **generator.py:** GenIce API isolation layer
- **ranker.py:** Pluggable ranking algorithms
- **data/phases.yaml:** Configuration over code

## Architectural Patterns

### Pattern 1: Pipeline Architecture

**What:** Sequential data flow with clear boundaries
**When to use:** When each stage has distinct responsibility
**Trade-offs:** Simple, testable; less flexible than event-driven

### Pattern 2: Wrapper Pattern

**What:** Wrap external library (GenIce) with internal interface
**When to use:** When integrating third-party code
**Trade-offs:** Decouples from library changes; adds indirection

### Pattern 3: Strategy Pattern

**What:** Pluggable ranking algorithms
**When to use:** When multiple ranking approaches exist
**Trade-offs:** Extensible; adds complexity

## Data Flow

### Request Flow

```
User CLI Args → Validator → Phase Mapper → GenIce (×N) → Ranker → PDB Writer → Files
    ↓              ↓              ↓             ↓           ↓           ↓
  Raw input   Normalized    Phase list    Structures   Ranked      Output
```

### Key Data Flows

1. **Generation flow:** T,P,N → validated → phases → coordinates → ranked → saved
2. **Ranking flow:** Multiple GenIce outputs → score → sort → top 10

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 1-100 structures | Sequential GenIce calls fine |
| 100-1000 structures | Parallel GenIce calls |
| 1000+ structures | Batch processing, caching |

### Scaling Priorities

1. **First bottleneck:** GenIce generation time — parallelize
2. **Second bottleneck:** Ranking computation — vectorize with NumPy

## Anti-Patterns

### Anti-Pattern 1: Tight Coupling to GenIce Internals

**What people do:** Directly accessing GenIce stage outputs
**Why it's wrong:** Internal APIs change between versions
**Do this instead:** Use only public API (formatter hooks)

### Anti-Pattern 2: Complex ML for Simple Phase Lookup

**What people do:** Neural network for phase selection
**Why it's wrong:** Rule-based lookup is faster and accurate for known phases
**Do this instead:** Start simple, add ML when baseline exists

### Anti-Pattern 3: Single-Pass Ranking

**What people do:** Rank once, return
**Why it's wrong:** May miss better candidates
**Do this instead:** Consider regeneration for top candidates

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| GenIce | Python import | Use as coordinate generator |
| spglib | Python import | Space group validation |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| CLI ↔ Core | Function call | Simple, direct |
| Core stages | Data objects | Typed dataclasses |

## Sources

- [GenIce2 GitHub](https://github.com/vitroid/GenIce) — Ice structure generation with 7-stage pipeline
- [GenIce README](https://github.com/vitroid/GenIce/blob/main/README.md) — Supported ice phases and usage
- [Spglib](https://github.com/spglib/spglib) — Crystal symmetry detection

---
*Architecture research for: ML-based ice structure generation*
*Researched: 2026-03-26*
