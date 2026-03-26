# Feature Research

**Domain:** ML-based ice structure generation
**Researched:** 2026-03-26
**Confidence:** MEDIUM-HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Temperature input | Ice phases are T-dependent | LOW | Standard numerical input (K) |
| Pressure input | Ice phases depend on P | LOW | Standard numerical input (MPa/bar) |
| Molecule count | System size control | LOW | Determines supercell |
| PDB output | Universal molecular format | LOW | Compatible with visualization |
| Ranked candidates | Know which most stable | LOW | Energy-based ranking |
| 10 candidates | polymorph exploration | LOW | QuickIce requirement |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| MLIP-based relaxation | Orders of magnitude faster than DFT | HIGH | Requires MACE/UMA integration |
| Sub-minute generation | Real-time feedback | HIGH | Requires optimized pipeline |
| Lightweight footprint | Runs on laptops | HIGH | No HPC required |
| T,P-aware ranking | Ranks by free energy at conditions | HIGH | Requires phonon calculations |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| DFT-level accuracy | Historical standard | MLIPs are faster but less accurate | Be explicit about MLIP accuracy |
| Exhaustive space group search | Thoroughness | 230 space groups prohibitive | Intelligent sampling (common ice phases) |
| GUI-first design | Modern UX | Scientists prefer CLI for batch | CLI-first |
| Single-threaded | Simplicity | Ignores available cores | Parallelize generation |

## Feature Dependencies

```
Input Parameters
    └──requires──> Condition Validator
                        └──requires──> Phase Mapper (T,P → phase)
                                                └──requires──> GenIce Generator
                                                                        └──requires──> Ranker
                                                                                └──requires──> PDB Writer
```

### Dependency Notes

- **Input Parameters requires Condition Validator:** Must validate T,P ranges before mapping
- **Phase Mapper requires GenIce Generator:** Generate actual coordinates for mapped phases
- **Ranker requires GenIce Generator:** Need structures to rank

## MVP Definition

### Launch With (v1)

- [ ] CLI with --temperature, --pressure, --nmolecules flags — essential interface
- [ ] Rule-based T,P → phase mapping — MVP doesn't need ML
- [ ] GenIce integration for coordinate generation — proven, valid outputs
- [ ] Energy-based ranking — simple scoring
- [ ] Top 10 PDB output — primary deliverable
- [ ] Basic validation (no overlap, valid space group) — ensure validity

### Add After Validation (v1.x)

- [ ] ML-based phase prediction — once rule-based baseline exists
- [ ] Phase identification — match outputs to known phases
- [ ] Confidence scoring — indicate ranking reliability

### Future Consideration (v2+)

- [ ] Free energy at T,P — requires phonon calculations
- [ ] GPU acceleration — profile first
- [ ] REST API — after core works
- [ ] Interactive visualization — CLI-first

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| CLI interface | HIGH | LOW | P1 |
| GenIce integration | HIGH | MEDIUM | P1 |
| Ranked PDB output | HIGH | LOW | P1 |
| T,P → phase mapping | HIGH | LOW | P1 |
| ML enhancement | MEDIUM | HIGH | P2 |
| GPU acceleration | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | GenIce | Other CSP Tools | Our Approach |
|---------|--------|-----------------|--------------|
| CLI interface | Yes | Yes | Simple flags only |
| ML-based ranking | No | Yes | Add ML ranking |
| Condition input | Manual | Yes | T,P,N as flags |
| PDB output | Yes | Yes | Direct output |

## Sources

- [GenIce2 GitHub](https://github.com/vitroid/GenIce) — Physics-based ice structure generation
- [Genarris 3.0](https://github.com/Yi5817/Genarris) — Random molecular crystal generator
- [XtalOpt](https://github.com/xtalopt/XtalOpt) — Evolutionary algorithm for crystal structure prediction
- [MACE-OFF](https://github.com/ACEsuit/mace-off) — Machine learning force field for organic molecules
- [UMA](https://huggingface.co/facebook/UMA) — Universal Model for Atoms
- [FAIRChem](https://github.com/facebookresearch/fairchem) — Meta FAIR Chemistry library (includes UMA)

---
*Feature research for: ML-based ice structure generation*
*Researched: 2026-03-26*
