# Pitfalls Research

**Domain:** ML-based ice structure generation
**Researched:** 2026-03-26
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Ice Rule Violations

**What goes wrong:**
ML generates water molecules with incorrect hydrogen bonding topology. Each water must have exactly 4 hydrogen bonds (2 donor, 2 acceptor).

**Why it happens:**
Pure ML approaches lack explicit enforcement of topological constraints. Neural networks learn spatial patterns but not graph-theoretic requirements.

**How to avoid:**
Use hybrid approach: ML predicts phase/conditions, GenIce generates valid coordinates.

**Warning signs:**
- analice validation fails
- Molecules with 3 or 5 bonds
- Non-tetrahedral angles
- Non-zero net dipole

**Phase to address:**
GenIce Integration Phase (use GenIce for generation)

---

### Pitfall 2: Phase Ordering Confusion

**What goes wrong:**
Model confuses ordered/disordered phase pairs (ice Ih/XI, ice III/IX).

**Why it happens:**
Most databases store only oxygen positions; hydrogen configuration under-reported.

**How to avoid:**
Use clear naming conventions; use GenIce's known phase templates.

**Warning signs:**
- Predicted ice IX above ~140 K
- Phase inconsistent with T,P input

**Phase to address:**
Phase Mapping Phase (validate against phase diagram)

---

### Pitfall 3: Density Mismatches

**What goes wrong:**
Generates dense structures for low-pressure phases, or vice versa.

**Why it happens:**
ML models default to mean densities without explicit density supervision.

**How to avoid:**
Include density as explicit feature; use GenIce's density scaling.

**Warning signs:**
- Ice VI with density < 1.2 g/cm³
- Generated density doesn't match expected phase

**Phase to address:**
GenIce Integration Phase (use density flags)

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip validation | Faster output | Invalid structures | Never |
| Hardcode phase list | Simplicity | Maintenance burden | MVP only |
| Single ranking pass | Simplicity | Miss best candidates | MVP only |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| GenIce | Accessing internal attributes | Use public API only |
| PDB writing | Missing CRYST1 record | Include cell parameters |
| spglib | Wrong cell format | Pass (lattice, positions, numbers) |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Sequential GenIce calls | Slow generation | Parallelize | >5 candidates |
| Large in-memory structures | Memory error | Stream PDB output | >1000 molecules |
| Unoptimized ranking | Slow ranking | Vectorize with NumPy | >50 candidates |

## Security Mistakes

Domain-specific security issues are minimal for this CLI tool (no network, no user data).

| Mistake | Risk | Prevention |
|---------|------|------------|
| Shell injection via args | Code execution | Use Click's type validation |
| Path traversal in output | File overwrite | Sanitize output paths |

## "Looks Done But Isn't" Checklist

- [ ] **PDB output:** Often missing CRYST1 record — verify unit cell present
- [ ] **Ranking:** Often uses unsorted output — verify files named by rank
- [ ] **Validation:** Often skipped in MVP — verify basic checks exist
- [ ] **GenIce integration:** Often tightly coupled — verify public API only

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Ice rule violations | HIGH | Regenerate with GenIce, add validation |
| Wrong phase output | MEDIUM | Fix phase mapper lookup table |
| Invalid PDB | LOW | Add CRYST1 record, fix atom naming |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Ice rule violations | GenIce Integration | Run analice on output |
| Phase ordering | Phase Mapping | Validate against phase diagram |
| Density mismatches | GenIce Integration | Check generated density |
| Shell injection | CLI Implementation | Use Click types only |

## Sources

- [GenIce2 GitHub](https://github.com/vitroid/GenIce) — Ice structure generation
- [GenIce README](https://github.com/vitroid/GenIce/blob/main/README.md) — Phase list and validation
- [analice2](https://github.com/vitroid/GenIce/tree/main/GenIce/Utilities) — Ice rule validation

---
*Pitfalls research for: ML-based ice structure generation*
*Researched: 2026-03-26*
