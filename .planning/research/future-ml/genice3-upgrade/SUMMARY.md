# Research Summary: GenIce3 Upgrade Assessment

**Domain:** Ice/hydrate structure generation library upgrade
**Researched:** 2026-06-27
**Overall confidence:** MEDIUM-HIGH

## Executive Summary

GenIce3 (v3.0b3 on PyPI, v3.0b4 on GitHub main) is a major API rewrite of the ice structure generation library that QuickIce depends on. The upgrade offers significant benefits — direct TIP4P/Ice generation, CIF crystal input, spot ions, cage survey JSON — but is blocked by two hard issues: Python 3.14 incompatibility (GenIce3 requires `<3.14`, QuickIce runs 3.14.3) and mutually exclusive `genice-core` version requirements. The Python 3.14 bound is conservative (genice-core itself has no upper bound, GenIce2 supports 3.14), and a one-line pyproject.toml patch resolves it. However, GenIce3 is still beta with no stable release timeline. Our recommendation is **GO LATER** — engage upstream now to resolve blockers, then migrate when GenIce3 3.0.0 stable + Python 3.14 support land (estimated Q3-Q4 2026).

The API migration is mechanically straightforward: only 2 main files (generator.py, hydrate_generator.py) need full rewrites of their GenIce integration, plus ~5 files with minor updates. GRO output format is 100% compatible, so our gro_parser.py and downstream pipeline remain unchanged. The total effort estimate is 6-11 days, with 2-3 days on the critical path.

## Key Findings

**Stack:** GenIce3 + genice-core≥1.5.4 + pyyaml + jinja2 + cif2ice (pip-only); fastapi/uvicorn are a packaging bug
**Architecture:** Reactive DependencyEngine replaces fixed 7-stage pipeline; inverted call pattern (Exporter.dumps(genice) vs genice.generate_ice(formatter))
**Critical pitfall:** Python 3.14 upper bound is conservative but prevents pip install; genice-core versions are mutually exclusive (no coexistence)

## Implications for Roadmap

Based on research, suggested phase structure for a future GenIce3 migration milestone:

1. **Phase 0: Upstream Engagement** — File Python 3.14 support issue + PR on GenIce3 GitHub; file packaging bug report for fastapi/uvicorn. No code changes. 30 min effort.
   - Addresses: Python 3.14 blocker
   - Avoids: Fork maintenance burden

2. **Phase 1: Proof of Concept** — Create prototype branch with patched GenIce3; validate API changes on Python 3.14; verify GRO output compatibility; verify sH cage naming. 1-2 weeks.
   - Addresses: API migration uncertainty, Python 3.14 runtime validation
   - Avoids: Premature full migration on beta software

3. **Phase 2: Core Migration** — Rewrite generator.py and hydrate_generator.py for GenIce3 API; update environment.yml; adapt gromacs_writer.py for `water_model="ice"`. 2-3 days.
   - Addresses: GenIce2→GenIce3 API transition
   - Avoids: GRO format breakage (confirmed compatible)

4. **Phase 3: Test & Validation** — Update all test fixtures; verify round-trip GRO→structure→GROMACS export; PyInstaller verification; sH cage naming validation. 2-3 days.
   - Addresses: Regression risk
   - Avoids: Subtle GRO format differences (confirmed identical)

5. **Phase 4: Cleanup & Feature Adoption** — Remove 3→4 atom normalization code; update GUI URLs/citations; add cage survey integration; add CIF input support. 2-3 days.
   - Addresses: Code simplification, new feature leverage
   - Avoids: Carrying dead normalization code

**Phase ordering rationale:**
- Phase 0 must come first (resolve blockers before any code work)
- Phase 1 validates feasibility before committing to full migration
- Phase 2-3 are the minimal viable migration
- Phase 4 is value-add that depends on Phase 2-3 being stable

**Research flags for phases:**
- Phase 1: Needs actual GenIce3 installation (Python 3.14 patch required)
- Phase 1: sH cage naming needs cage_survey verification (can't be done without GenIce3 installed)
- Phase 2: `water_model="ice"` MW position must be verified against our TIP4P-ICE constants
- Phase 3: PyInstaller hidden imports for GenIce3 may differ from GenIce2

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All dependencies verified from pyproject.toml + conda-forge |
| API Migration | HIGH | All 13 GenIce2→GenIce3 calls mapped with working code examples |
| Features | HIGH | Comprehensive inventory from official docs + source code |
| Architecture | MEDIUM-HIGH | DependencyEngine described but no benchmarks; behavioral details may differ |
| Pitfalls | HIGH | Python 3.14 bound confirmed conservative; genice-core conflict confirmed irreconcilable |
| Migration Effort | MEDIUM | ~130-200 LOC changes estimated; may vary with unforeseen issues |
| Timeline | LOW | No stable release date; 3-6 month estimate is speculative |

## Gaps to Address

- **sH cage naming in GenIce3**: Current code uses "16" for sH large cage (possibly incorrect even in GenIce2). GenIce3 uses "A" prefix. Exact mapping needs cage_survey verification.
- **`ice1h` vs `ice1h_unit` axis convention**: GenIce3 warns about historical axis swap. Need empirical comparison.
- **`water_model="ice"` MW position**: Must verify GenIce3's TIP4P-ICE MW distance matches our `TIP4P_ICE_MW_DIST` constant.
- **GenIce3 3.0.0 release date**: Unknown. No roadmap, no milestones on GitHub.
- **Maintainer responsiveness**: GenIce3 has 2 stars, 0 forks. Unknown if PRs will be reviewed.
