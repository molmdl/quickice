# GenIce3 Upgrade Research Plan

**Created:** 2026-06-27
**Scope:** Research-only — no installation or code changes
**Output directory:** `.planning/research/future-ml/genice3-upgrade/`
**Context:** Future milestone assessment for upgrading from GenIce2==2.2.13.1 to GenIce3

---

## Executive Summary (Preliminary Findings)

GenIce3 **exists** on PyPI at version **3.0b3** (pre-release, Feb 26 2026) under a new GitHub org (`genice-dev/GenIce3`). It is a **major API rewrite** with a reactive pipeline architecture. Two **hard blockers** prevent immediate adoption:

1. **Python version**: GenIce3 requires `<3.14, >=3.11`. QuickIce runs Python 3.14.3.
2. **genice-core conflict**: GenIce2 pins `genice-core>=1.2,<1.3`. GenIce3 requires `>=1.5.4,<2.0.0`. They **cannot coexist**.

Additionally, GenIce3 introduces **new heavy dependencies** (fastapi, uvicorn) and the API is completely rewritten. GROMACS export IS still supported.

---

## Research Tasks

### Task 1: API Migration Map (GenIce2 → GenIce3)

**Priority:** CRITICAL — must be done first
**Output:** `01-API-MIGRATION-MAP.md`

Map every GenIce2 API call in QuickIce to its GenIce3 equivalent. Our codebase uses 7 specific GenIce2 APIs:

| GenIce2 API | QuickIce Usage | GenIce3 Equivalent (Tentative) |
|---|---|---|
| `from genice2.genice import GenIce` | Both generator.py, hydrate_generator.py | `from genice3.genice import GenIce3` |
| `from genice2.plugin import safe_import` | Both files | `from genice3.plugin import UnitCell, Exporter, Molecule` |
| `GenIce(lattice, density=, reshape=)` | generator.py:111, hydrate_generator.py:161 | `GenIce3()` then `genice.set_unitcell(name, density=)` + `replication_matrix=` |
| `safe_import('lattice', name).Lattice()` | generator.py:108, hydrate_generator.py:151 | `genice.set_unitcell(name)` or `UnitCell(name)` |
| `safe_import('molecule', 'tip3p').Molecule()` | generator.py:119 | water model as exporter suboption: `Exporter("gromacs").dump(genice, water_model="tip3p")` |
| `safe_import('format', 'gromacs').Format()` | generator.py:122, hydrate_generator.py:167 | `Exporter("gromacs")` |
| `ice.generate_ice(formatter=, water=, guests=, depol=)` | generator.py:125, hydrate_generator.py:208 | `Exporter("gromacs").dump(genice, water_model="tip4p")` |
| `from genice2.valueparser import parse_guest` | hydrate_generator.py:146 | `from genice3.cli.options import parse_guest_option` |
| `from genice2.lattices import sI, sII, sH` | hydrate_generator.py:64 | `UnitCell("CS1")`, `UnitCell("CS2")`, `UnitCell("DOH")` |
| `from genice2.molecules.tip4p import Molecule as TIP4P` | hydrate_generator.py:65 | water model as exporter suboption |

**Research questions to answer:**

1. How does `Exporter("gromacs").dump()` return output? GenIce2's `generate_ice()` returns a GRO string — does GenIce3's `dump()` return a string? Write to stdout? Write to file? This is critical because QuickIce parses the GRO string.
2. How do `parse_guest_option` cage names work? GenIce2 uses numeric cage IDs ("12", "14", "16"). GenIce3 examples show prefixed names ("A12", "A14"). Is this consistent? What are the exact cage name mappings for sI, sII, sH?
3. How does GenIce3 handle the `depol` parameter? GenIce2 uses `depol='strict'`. GenIce3 examples show `pol_loop_1=2000`. Is `depol` still available? What's the equivalent?
4. How does `replication_matrix` relate to GenIce2's `reshape`? Same numpy array format?
5. How does `seed` work in GenIce3? GenIce2 uses global `np.random.seed()`. GenIce3 has `seed=42` as a constructor parameter. Does it use the newer Generator API?
6. What is the exact `generate_ice` equivalent for producing a GRO string from GenIce3?

**Sources to consult:**
- https://genice-dev.github.io/GenIce3/for-ai-assistants.html
- https://genice-dev.github.io/GenIce3/api-examples/basic.html
- https://genice-dev.github.io/GenIce3/api-examples/guest_occupancy.html
- https://github.com/genice-dev/GenIce3 (source code for GenIce3 class)
- Our existing `.planning/research/GENICE2_API_RESEARCH.md`

---

### Task 2: Dependency & Compatibility Analysis

**Priority:** CRITICAL
**Output:** `02-DEPENDENCY-COMPATIBILITY.md`

Document all version conflicts, new dependencies, and compatibility requirements.

**Known findings so far:**

| Dependency | GenIce2 Requirement | GenIce3 Requirement | QuickIce Current | Conflict? |
|---|---|---|---|---|
| Python | >=3.10 | >=3.11, **<3.14** | 3.14.3 | **YES — HARD BLOCKER** |
| genice-core | >=1.2, **<1.3** | **>=1.5.4**, <2.0.0 | 1.4.3 | **YES — MUTUALLY EXCLUSIVE** |
| numpy | >=2.0 | >=2.0 | 2.4.3 | No |
| networkx | >=2.0 | >=2.0 | 3.6.1 | No |
| scipy | not required | not required | 1.17.1 | No |
| pairlist | >=0.6.4 | >=0.6.4 | 0.6.4 | No |
| cycless | >=0.4.2 | **>=0.7** | 0.7 | No (already meets) |
| graphstat | >=0.3.3 | >=0.3.3 | 0.3.3 | No |
| yaplotlib | >=0.1.2 | >=0.1.2 | 0.1.3 | No |
| openpyscad | >=0.5.0 | >=0.5.0 | 0.5.0 | No |
| deprecation | >=2.1.0 | **removed** | 2.1.0 | GenIce3 drops it |
| pyyaml | not required | **>=6.0** | not installed | **NEW** |
| jinja2 | not required | **>=3.1.4** | not installed | **NEW** |
| cif2ice | not required | **>=0.4.1,<0.5.0** | not installed | **NEW** |
| fastapi | not required | **>=0.135.3,<0.136.0** | not installed | **NEW — unexpected for ice generator** |
| uvicorn | not required | **>=0.44.0,<0.45.0** | not installed | **NEW — web server dependency** |

**Research questions to answer:**

1. Why does GenIce3 depend on fastapi/uvicorn? Is this optional? Is it for a web visualization server? Can it be excluded?
2. Will Python 3.14 support be added to GenIce3? Check GitHub issues and recent commits for Python 3.14 compatibility plans.
3. What changed in genice-core 1.5.4 vs 1.4.3? Is the API change fundamental?
4. Can genice2 and genice3 coexist in the same environment at all (even with incompatible genice-core)?
5. Are there any conda-forge packages for genice3, pyyaml, jinja2, cif2ice, fastapi, uvicorn?

**Sources to consult:**
- https://pypi.org/project/genice3/3.0b3/ (dependency list)
- https://github.com/genice-dev/GenIce3 (pyproject.toml for exact deps)
- https://github.com/genice-dev/genice-core (changelog between 1.4.3 and 1.5.4+)
- https://github.com/genice-dev/GenIce3/issues (search for Python 3.14)

---

### Task 3: Migration Impact Assessment for QuickIce

**Priority:** HIGH (depends on Task 1 and Task 2)
**Output:** `03-MIGRATION-IMPACT.md`

Enumerate every code change needed to migrate from GenIce2 to GenIce3, estimate effort, and identify risks.

**Files that need changes:**

| File | GenIce2 Usage | Approximate Change Scope |
|---|---|---|
| `quickice/structure_generation/generator.py` | `safe_import`, `GenIce`, `generate_ice`, `safe_import('molecule','tip3p')`, `safe_import('format','gromacs')` | Major rewrite of `_generate_single()` method |
| `quickice/structure_generation/hydrate_generator.py` | `GenIce`, `safe_import`, `parse_guest`, `sI/sII/sH` imports, `TIP4P` import, `generate_ice` | Major rewrite of `_run_via_api()` and `_ensure_genice_import()` |
| `quickice/structure_generation/mapper.py` | Maps phase IDs to GenIce2 lattice names | May need lattice name mapping updates |
| `quickice/structure_generation/gro_parser.py` | Parses GRO output from GenIce | Likely no change needed (GRO format unchanged) |
| `environment.yml` | `genice2==2.2.13.1`, `genice-core==1.4.3` | Replace with genice3 + new dependencies |
| All test files using GenIce2 fixtures | conftest.py fixtures generate real structures | May need API call updates |
| `quickice-gui.spec` (PyInstaller) | GenIce2 hiddenimports | Update for GenIce3 module structure |

**Research questions to answer:**

1. Does GenIce3's GRO output format exactly match GenIce2's? Same atom naming conventions (OW, HW1, HW2, MW for TIP4P; O, H, H for TIP3P)? Same residue naming (SOL, CH4, THF)?
2. Does the `--seed` / `seed=` parameter produce deterministic output the same way as GenIce2's `np.random.seed(seed)`?
3. Are there any new lattice names or renamed lattices in GenIce3 vs GenIce2? (e.g., is "1h" still "1h"?)
4. What is the exact GRO string retrieval mechanism? We need a string, not a file.
5. Risk assessment: What's the blast radius if we need to support BOTH GenIce2 and GenIce3 during a transition period?

**Sources to consult:**
- https://genice-dev.github.io/GenIce3/output-formats.html (GROMACS exporter details)
- https://genice-dev.github.io/GenIce3/unitcells.html (lattice name mapping)
- https://github.com/genice-dev/GenIce3/tree/main/examples/api (working code examples)
- Our codebase: `generator.py`, `hydrate_generator.py`, `gro_parser.py`, `mapper.py`

---

### Task 4: New Feature Inventory & Relevance

**Priority:** MEDIUM
**Output:** `04-NEW-FEATURES.md`

Catalog new GenIce3 features and assess which are relevant to QuickIce's roadmap.

**New features to investigate:**

| Feature | Description | QuickIce Relevance |
|---|---|---|
| **Protonic defects** (H₃O⁺, OH⁻) | API-only defect embedding | Potentially relevant for future "doped ice" work |
| **Bjerrum defects** (L/D type) | Topological defects in HB network | Low — niche scientific use |
| **Spot ions** (-A/-C) | Replace specific water molecules, not just unit-cell sites | Medium — more flexible than GenIce2's unit-cell-only ion doping |
| **Reactive pipeline** (DependencyEngine) | Auto-computes only what's needed | Internal change, no direct user benefit |
| **Config file support** (YAML) | genice3 --config file.yaml | CLI convenience only |
| **LAMMPS export** | New output format | Low — QuickIce is GROMACS-focused |
| **Cage survey exporter** | JSON cage positions/types | Medium — could improve hydrate UI info |
| **Plotly 3D visualization** | Interactive HTML output | Low — we use VTK |
| **CIF input as unit cell** | genice3 CIF --file path.cif | Medium — could support arbitrary ice structures |
| **New unit cells**: Ice XXI, prism, aeroice | Additional ice phases | Low — niche, not in our phase diagram |
| **Water model as suboption** | `-e gromacs :water_model tip5p` | Medium — cleaner API for water model selection |

**Research questions to answer:**

1. Are there any new experimentally verified ice phases that would expand QuickIce's phase diagram coverage?
2. Can the protonic defect API be used to generate ionic solutions (relevant to our ion insertion workflow)?
3. Is the cage survey exporter useful for pre-generating cage info to display in our hydrate UI?

---

### Task 5: Upgrade Pathway Recommendation

**Priority:** HIGH (depends on Tasks 1-3)
**Output:** `05-UPGRADE-RECOMMENDATION.md`

Synthesize all findings into a clear recommendation with decision criteria.

**Key decision factors to evaluate:**

1. **Blocker timeline**: When will GenIce3 support Python 3.14? When will a stable (non-beta) release ship?
2. **Coexistence strategy**: Can we write an adapter layer that supports both GenIce2 and GenIce3 with runtime detection?
3. **Minimum viable migration**: What's the smallest change set that gets us onto GenIce3?
4. **Risk of staying on GenIce2**: Is GenIce2 still maintained? Will genice-core 1.2.x get Python 3.14 support?
5. **Beta risk**: Is GenIce3 3.0b3 stable enough for scientific use? Are there known bugs?
6. **Alternative approaches**: Could we fork genice-core 1.4.x for Python 3.14 compatibility? Could we patch GenIce3's Python constraint?

**Output should include:**

- Go/no-go recommendation with confidence level
- If "go later": specific conditions that must be met before upgrade
- If "go now": migration plan outline with effort estimate
- Risk register with mitigation strategies

---

## Execution Plan

### Wave 1 (Parallel — independent research)

| Task | Agent Focus | Output |
|---|---|---|
| Task 1 | API migration map — source code + docs analysis | `01-API-MIGRATION-MAP.md` |
| Task 2 | Dependency compatibility — version conflict documentation | `02-DEPENDENCY-COMPATIBILITY.md` |
| Task 4 | New feature inventory — relevance to QuickIce roadmap | `04-NEW-FEATURES.md` |

### Wave 2 (Sequential — depends on Wave 1)

| Task | Agent Focus | Output |
|---|---|---|
| Task 3 | Migration impact assessment — code change enumeration | `03-MIGRATION-IMPACT.md` |
| Task 5 | Upgrade pathway recommendation — decision document | `05-UPGRADE-RECOMMENDATION.md` |

### Context Files for Research Agents

Each agent should reference:
- `@quickice/structure_generation/generator.py` — GenIce2 ice generation integration
- `@quickice/structure_generation/hydrate_generator.py` — GenIce2 hydrate generation integration
- `@quickice/structure_generation/mapper.py` — lattice name mapping
- `@quickice/structure_generation/gro_parser.py` — GRO format parsing
- `@quickice/environment.yml` — current dependency pins
- `@.planning/research/GENICE2_API_RESEARCH.md` — existing GenIce2 API reference

### Key External Sources

- **GenIce3 PyPI**: https://pypi.org/project/genice3/3.0b3/
- **GenIce3 GitHub**: https://github.com/genice-dev/GenIce3
- **GenIce3 Docs**: https://genice-dev.github.io/GenIce3/
- **AI-targeted overview**: https://genice-dev.github.io/GenIce3/for-ai-assistants.html
- **API examples**: https://genice-dev.github.io/GenIce3/api-examples/
- **GenIce2 (current) GitHub**: https://github.com/genice-dev/GenIce2
- **genice-core GitHub**: https://github.com/genice-dev/genice-core

---

## Critical Blocker Summary

### BLOCKER 1: Python 3.14 Incompatibility
- GenIce3 requires `Python <3.14, >=3.11`
- QuickIce runs Python 3.14.3
- **Resolution needed**: Either GenIce3 drops the `<3.14` upper bound, or QuickIce downgrades Python, or we find the specific incompatibility and patch it

### BLOCKER 2: genice-core Version Conflict
- GenIce2 requires `genice-core>=1.2,<1.3` (pins to 1.2.x only)
- GenIce3 requires `genice-core>=1.5.4,<2.0.0`
- These ranges are **mutually exclusive** — no single genice-core version satisfies both
- **Resolution needed**: Complete cutover (remove GenIce2 entirely) or maintain separate environments

### BLOCKER 3: Beta Status
- GenIce3 is at 3.0b3 (pre-release)
- Last release was Feb 26, 2026 (4 months ago)
- No stable 3.0.0 release yet
- **Resolution needed**: Wait for stable release, or accept beta risk

### CONCERN: Unexpected Heavy Dependencies
- GenIce3 requires fastapi + uvicorn (web framework + ASGI server)
- This is unusual for an ice structure generator
- **Resolution needed**: Determine if these are optional or fundamental; if fundamental, assess security/supply-chain risk

---

## Success Criteria

Research is complete when:

1. Every GenIce2 API call in QuickIce has a documented GenIce3 equivalent (or "no equivalent" with workaround)
2. All dependency conflicts are documented with proposed resolutions
3. Migration effort is estimated in terms of files modified and approximate OpenCode execution time
4. A go/no-go recommendation exists with clear decision criteria
5. All blocker resolutions are documented with expected timelines where possible
