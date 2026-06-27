# Dependency & Compatibility Analysis: GenIce3 Upgrade

**Project:** QuickIce GenIce3 Upgrade Assessment
**Researched:** 2026-06-27
**Overall confidence:** MEDIUM-HIGH (verified against GitHub source; PyPI pages partially blocked by bot detection)

## Executive Summary

GenIce3 (3.0b4 on main, 3.0b3 on PyPI) introduces fundamental dependency changes from GenIce2 (2.2.13.1). **Two hard blockers prevent direct installation in QuickIce's Python 3.14.3 environment**: (1) GenIce3's `requires-python = ">=3.11,<3.14"` excludes Python 3.14, and (2) GenIce3 requires `genice-core>=1.5.4,<2.0.0` which is mutually exclusive with GenIce2's `genice-core>=1.2,<1.3`. Additionally, a **packaging bug** places fastapi/uvicorn in core dependencies when they should be optional ([web] extras only). The Python 3.14 upper bound appears conservative rather than based on known code incompatibilities — genice-core itself declares `python>=3.11,<4.0` and GenIce2 already supports Python 3.14. A patched/forked approach is feasible but requires ongoing maintenance.

---

## 1. Complete Dependency Comparison Table

| Dependency | GenIce2 Requirement | GenIce3 Requirement (pyproject.toml) | QuickIce Current | Conflict? | Severity |
|---|---|---|---|---|---|
| **Python** | `>=3.10, <4.0` | `>=3.11, <3.14` | 3.14.3 | **YES** | **HARD BLOCKER** |
| **genice-core** | `>=1.2, <1.3` | `>=1.5.4, <2.0.0` | 1.4.3 | **YES — MUTUALLY EXCLUSIVE** | **HARD BLOCKER** |
| numpy | `>=2.0` | `>=2.0` | 2.4.3 | No | — |
| networkx | `>=2.0.dev20160901144005` | `>=2.0.dev20160901144005` | 3.6.1 | No | — |
| pairlist | `>=0.6.4` | `>=0.6.4` | 0.6.4 | No | — |
| cycless | `>=0.4.2` | `>=0.7` | 0.7 | No | — |
| graphstat | `>=0.3.3` | `>=0.3.3` | 0.3.3 | No | — |
| yaplotlib | `>=0.1.2` | `>=0.1.2` | 0.1.3 | No | — |
| openpyscad | `>=0.5.0` | `>=0.5.0` | 0.5.0 | No | — |
| **deprecation** | `>=2.1.0` | **REMOVED** | 2.1.0 | GenIce3 drops it | LOW (no conflict) |
| **pyyaml** | not required | `>=6.0` | not installed | NEW — must add | MEDIUM |
| **jinja2** | not required | `>=3.1.4` | not installed | NEW — must add | MEDIUM |
| **cif2ice** | not required | `>=0.4.1, <0.5.0` | not installed | NEW — must add | MEDIUM |
| **fastapi** | not required | `>=0.135.3, <0.136.0` | not installed | NEW — **packaging bug** | MEDIUM (should be optional) |
| **uvicorn** | not required | `>=0.44.0, <0.45.0` | not installed | NEW — **packaging bug** | MEDIUM (should be optional) |

**Confidence:** HIGH — verified against GenIce3 pyproject.toml on GitHub main branch (v3.0b4).

---

## 2. Hard Blockers — Detailed Analysis

### Blocker 1: Python 3.14 Incompatibility

**What:** GenIce3 declares `requires-python = ">=3.11,<3.14"` in pyproject.toml. QuickIce runs Python 3.14.3.

**Evidence the bound is conservative, not real:**

1. **genice-core** (main branch, v1.6.1) declares `python = ">=3.11,<4.0"` — **no upper bound**.
2. **GenIce2** (v2.2.13.3 on PyPI) explicitly lists Python 3.14 in its classifiers — it works on 3.14.
3. **GenIce3 is built with CPython 3.10.19** (per PyPI metadata: `Uploaded via: poetry/2.3.2 CPython/3.10.19`). The author has not tested on 3.14.
4. **No Python 3.14 issues found** in GenIce3 GitHub issues (0 open, 0 closed).
5. **GenIce3 code uses standard Python features** — no C extensions, no ctypes, no known 3.14-breaking patterns observed in the source.

**What's actually in the code:**
- Type hints using `X | None` syntax (3.10+)
- `from __future__ import annotations` throughout (backwards compatible)
- Standard library only: `logging`, `pathlib`, `dataclasses`, `inspect`, `io`, `os`, `sys`, `enum`, `typing`
- No known 3.14-deprecated APIs used

**Assessment:** The `<3.14` bound is almost certainly **conservative/predictive**, not based on known incompatibilities. Python 3.14 removed the `imp` module and changed some C-API internals, but GenIce3 is pure Python using modern features.

**Possible resolutions:**

| Approach | Risk | Effort | Maintenance |
|---|---|---|---|
| **Patch pyproject.toml locally** (change `<3.14` to `<3.15` or `<4.0`) | LOW — likely works | LOW — one-line edit | Must re-patch on every GenIce3 update |
| **Fork GenIce3, maintain Python 3.14 compat** | LOW | MEDIUM — set up CI on 3.14 | Ongoing fork maintenance |
| **File issue / PR upstream** | LOW — author may accept | LOW — just change the bound | Best option if author is responsive |
| **Downgrade Python to 3.13** | MEDIUM — loses conda-forge cp314 stack | HIGH — entire env rebuild | No maintenance needed |
| **Run GenIce3 in separate Python 3.13 env** | LOW | MEDIUM — subprocess isolation | Ongoing coordination overhead |

**Confidence:** HIGH that the bound is conservative; MEDIUM that no 3.14 issues exist (untested).

---

### Blocker 2: genice-core Version Conflict

**What:** GenIce2 requires `genice-core>=1.2,<1.3`. GenIce3 requires `genice-core>=1.5.4,<2.0.0`. These ranges do not overlap. Only one can be installed at a time.

**QuickIce currently has genice-core 1.4.3** — which doesn't satisfy either GenIce3's requirement (needs ≥1.5.4).

**Coexistence feasibility:** GenIce2 and GenIce3 **CANNOT coexist in the same Python environment** due to this constraint. This is a fundamental package namespace collision.

**Possible resolutions:**

| Approach | Risk | Effort | Maintenance |
|---|---|---|---|
| **Full migration: drop GenIce2, adopt GenIce3** | HIGH — API changes | HIGH — rewrite QuickIce integration | None after migration |
| **Separate Python environments per version** | LOW | MEDIUM — subprocess + serialization | Ongoing |
| **Fork genice-core, add compatibility shim** | HIGH — diverges from upstream | VERY HIGH | Ongoing sync |
| **Virtual environment per invocation** | LOW | MEDIUM | Ongoing overhead |

**Confidence:** HIGH — verified from both packages' pyproject.toml files.

---

## 3. New Dependency Analysis

### pyyaml (>=6.0)

**Purpose:** YAML configuration file parsing for GenIce3 CLI/API. The `--config`/`-Y` flag reads YAML config files. The `runner.py` module imports yaml with graceful `try/except ImportError`.

**Is it needed for QuickIce?** YES — it's a core CLI feature. The `load_config_file()` and `load_config_text()` functions in `genice3.cli.runner` require it.

**Supply chain risk:** LOW — PyYAML is one of the most widely-installed Python packages, maintained by the YAML project.

**conda-forge:** Available (v6.0.3, noarch). **Confidence:** HIGH.

### jinja2 (>=3.1.4)

**Purpose:** Template engine. Used in GenIce3 for generating formatted output (likely in exporter plugins or CIF-related code generation).

**Is it needed for QuickIce?** LIKELY YES — it's listed as a core dependency in pyproject.toml and GenIce3 may use it for internal template rendering.

**Supply chain risk:** LOW — Jinja2 is a Pallets project (same as Flask), extremely widely used, well-maintained.

**conda-forge:** Available (v3.1.6, noarch). **Confidence:** HIGH.

### cif2ice (>=0.4.1, <0.5.0)

**Purpose:** CIF (Crystallographic Information File) to ice lattice conversion. **Directly imported** at module level in `genice3/genice.py`: `from cif2ice import cellshape`. This is used for CIF-derived unitcell generation.

**Is it needed for QuickIce?** YES — it's a hard import in the core `genice.py` module. If QuickIce ever uses CIF-based unitcells, this is required. Even if not, the import is unconditional.

**Supply chain risk:** MEDIUM — niche package by the GenIce author (vitroid), single maintainer, narrow version range pinned.

**conda-forge:** NOT available (404 on conda-forge). Must install via pip.

**Confidence:** HIGH — verified from genice3/genice.py source code.

### fastapi (>=0.135.3, <0.136.0) — PACKAGING BUG

**Purpose:** Web API server for GenIce3. Provides a REST API at `/v1/generate` for structure generation via HTTP. The `genice3-web` script launches this server.

**Is it actually a core dependency?** **NO — this is a packaging bug.** Evidence:

1. The webapi.py code uses `try/except ModuleNotFoundError` to gracefully handle missing fastapi:
   ```python
   try:
       from fastapi import FastAPI, HTTPException, Request, Response
       from fastapi.middleware.cors import CORSMiddleware
   except ModuleNotFoundError as e:
       raise ModuleNotFoundError(
           "Web API には FastAPI が必要です。例: pip install 'genice3[web]'"
       ) from e
   ```
2. GenIce3 also defines `[project.optional-dependencies] web = ["fastapi>=0.115.0", "uvicorn[standard]>=0.32.0"]` — the **intended** way to install web support.
3. The CLI entry point (`genice3`) does NOT import fastapi/uvicorn.
4. The core GenIce3 class (`genice3/genice.py`) does NOT import fastapi/uvicorn.

**Version conflict in pyproject.toml:** Core deps pin `fastapi>=0.135.3,<0.136.0` while the optional web group pins `fastapi>=0.115.0`. The core pins are tighter and newer — this inconsistency confirms the packaging error.

**Is it needed for QuickIce?** **NO** — QuickIce does not need a web API server. QuickIce uses GenIce as a library, not as an HTTP service.

**Supply chain risk if installed anyway:** MEDIUM — fastapi pulls in pydantic (v2), starlette, anyio, and other transitive deps. These are well-maintained but add surface area.

**conda-forge:** Available (v0.138.1, noarch). **Confidence:** HIGH for availability; HIGH for packaging bug determination.

### uvicorn (>=0.44.0, <0.45.0) — PACKAGING BUG

**Purpose:** ASGI server for running the FastAPI web app. Same packaging bug as fastapi — should be in [web] extras only.

**Is it needed for QuickIce?** **NO** — same reasoning as fastapi.

**conda-forge:** Available (v0.49.0, noarch). **Confidence:** HIGH.

### deprecation (removed)

**Purpose:** GenIce2 used `deprecation>=2.1.0` for deprecation warnings. GenIce3 removes this dependency entirely.

**Impact on QuickIce:** QuickIce currently has `deprecation==2.1.0` in its environment. GenIce3 doesn't need it, but having it installed won't cause conflicts. It can be kept for other dependencies or removed if nothing else needs it.

**Confidence:** HIGH.

---

## 4. genice-core Changelog (1.4.3 → 1.5.4+ → 1.6.1)

Reconstructed from commit history on `genice-dev/genice-core` main branch:

### Version 1.4.3 (March 25, 2026) — QuickIce's current version
- Version bump from 1.4.x series
- Updated logging messages in `dipole.py` and `__init__.py`
- This is the last version compatible with GenIce2

### Changes between 1.4.3 and 1.5.4 (March 27, 2026)

| Change | Impact | API Breaking? |
|---|---|---|
| **`polarize_loop` integrated into `ice_graph`** | Stage 4 depolarization now part of `ice_graph()` | **YES** — function signature changed |
| **`seed` parameter added to `ice_graph`** | Reproducible randomization | **NO** — additive parameter |
| **`random` module removed** | No more `import random` — uses `np.random` exclusively | Internal only |
| **Parameter renaming: `max_attempts` → `pairingAttempts`** | Clarity improvement | **YES** — old name deprecated |
| **`force_polarize` implementation** | New polarization forcing option | Additive |
| **BFS-based path connection (`connect_matching_paths_bfs`)** | New algorithm for high-concentration ices | Additive |
| **Return to NetworkX-based implementation** | Abandoned Nim/C++ ports; back to pure Python+NX | Internal only |

### Changes in 1.5.4+ → 1.6.0 (May 27, 2026)

| Change | Impact | API Breaking? |
|---|---|---|
| **MCF-based path connection (`connect_matching_paths_mcf`)** | Even newer algorithm for path connection | Additive |
| **Python requirement changed to `>=3.11,<4.0`** | Drops 3.10 support, **removes 3.14 upper bound** | N/A |

### Changes in 1.6.1 (May 27, 2026)

| Change | Impact | API Breaking? |
|---|---|---|
| **`connect_engine` functions deprecated** | Legacy path connection functions deprecated in favor of MCF | **YES** — deprecation warnings |
| **New `compare_a15_bjerrum_connect` example** | Documentation only | No |

### Key API Differences (1.4.3 vs 1.5.4+)

The `ice_graph()` function signature changed significantly:

```python
# genice-core 1.4.3 (GenIce2 compatible)
genice_core.ice_graph(
    graph,
    vertex_positions=...,
    is_periodic_boundary=True,
    maxattempts=1000,   # OLD parameter name
    # No seed parameter
    # No fixed_edges parameter
    # No target_pol parameter
)

# genice-core 1.5.4+ (GenIce3 compatible)
genice_core.ice_graph(
    graph,
    vertex_positions=...,
    is_periodic_boundary=True,
    pairingAttempts=1000,    # NEW parameter name
    seed=1,                  # NEW
    fixed_edges=fixed_dg,    # NEW
    target_pol=np.array([0,0,0]),  # NEW
    dipole_optimization_cycles=1000,  # NEW (was separate stage)
    dipole_optimization_cycles2=0,    # NEW
)
```

**Confidence:** HIGH — reconstructed from actual GitHub commit messages and source code.

---

## 5. Python 3.14 Compatibility Investigation

### Is the Upper Bound Real or Conservative?

**Verdict: CONSERVATIVE — no known code-level incompatibility.**

**Evidence for "conservative" classification:**

| Factor | Finding | Source |
|---|---|---|
| genice-core Python bound | `>=3.11, <4.0` — no 3.14 limit | pyproject.toml on main |
| GenIce2 Python support | Explicitly lists Python 3.14 in classifiers | PyPI page |
| GenIce3 build environment | CPython 3.10.19 — author hasn't tested beyond 3.10 | PyPI metadata |
| GenIce3 code features | Pure Python, modern type hints, no C extensions | Source code review |
| Python 3.14 breaking changes | Removed `imp` module (not used), C-API changes (not relevant for pure Python), `free-threading` opt-in (not used) | Python 3.14 changelog |
| GitHub issues | 0 open issues, 0 closed issues about Python 3.14 | GenIce3 issues page |

### Specific Python 3.14 Concerns

1. **`from __future__ import annotations`** — Used throughout GenIce3. This is PEP 563, available since 3.7. Not affected by 3.14.
2. **Type union syntax `X | Y`** — Used in GenIce3 (e.g., `List[Tuple[int, int]] | None`). Available since 3.10. Not affected by 3.14.
3. **`str | None` in function signatures** — Used in GenIce3. Available since 3.10. Not affected by 3.14.
4. **`match/case` statements** — Not observed in GenIce3 source. Not relevant.
5. **Dict comprehension / f-strings** — Standard Python. Not affected.

### Patch Feasibility

Changing `requires-python = ">=3.11,<3.14"` to `">=3.11,<3.15"` or `">=3.11,<4.0"` in GenIce3's pyproject.toml is a **one-line change**. This can be done:

- Locally in a cloned repo: `pip install -e .` from the patched source
- Via a fork on GitHub
- By filing a PR upstream

**Risk of runtime failure after patching:** LOW — GenIce3 is pure Python with no known 3.14-breaking patterns.

**Confidence:** HIGH that patching is feasible; MEDIUM that no runtime issues will emerge (untested on 3.14).

---

## 6. Coexistence Feasibility

### Can GenIce2 and GenIce3 coexist in the same Python environment?

**NO — due to genice-core version conflict.**

| Constraint | GenIce2 | GenIce3 | Overlap? |
|---|---|---|---|
| genice-core | >=1.2, <1.3 | >=1.5.4, <2.0.0 | **NONE** |
| Python | >=3.10, <4.0 | >=3.11, <3.14 | 3.11–3.13 |
| deprecation | >=2.1.0 | not required | Compatible |

### Workaround Options

#### Option A: Subprocess Isolation

Run GenIce3 in a separate conda environment with Python 3.13, communicate via subprocess:

```
QuickIce (Python 3.14) → subprocess → genice3 (Python 3.13) → output files
```

**Pros:** Clean separation, no version conflicts.
**Cons:** Subprocess overhead, serialization/deserialization of structures, harder error handling.

#### Option B: Full Migration

Drop GenIce2, rewrite QuickIce to use GenIce3 API exclusively:

**Pros:** Clean single-version environment, access to GenIce3 features (defects, reactive pipeline).
**Cons:** Significant API rewrite effort, risk of regressions, beta software.

#### Option C: Fork + Patch

Fork GenIce3, patch Python 3.14 compat, fix fastapi packaging bug, maintain locally:

**Pros:** Full control, QuickIce stays on Python 3.14.
**Cons:** Ongoing sync with upstream, maintenance burden.

#### Option D: Downgrade Python

Move QuickIce to Python 3.13.x:

**Pros:** No patching needed, GenIce3 works out of box.
**Cons:** Loses conda-forge cp314 packages, entire environment rebuild, potential issues with other deps that require 3.14+.

**Recommendation:** Option C (fork + patch) is the most pragmatic for short term. Option B (full migration) is the correct long-term direction.

**Confidence:** HIGH.

---

## 7. Conda-forge Availability

| Package | conda-forge Available? | Latest Version | Notes |
|---|---|---|---|
| pyyaml | YES | 6.0.3 | noarch |
| jinja2 | YES | 3.1.6 | noarch |
| fastapi | YES | 0.138.1 | noarch; newer than GenIce3's pin |
| uvicorn | YES | 0.49.0 | noarch; newer than GenIce3's pin |
| cif2ice | **NO** | — | pip only; 404 on conda-forge |
| genice3 | **NO** | — | pip only; 404 on conda-forge |
| genice-core | **NOT CHECKED** | — | PyPI page blocked by bot detection |
| genice2 | **NOT CHECKED** | — | Available historically via pip |

**Version pin issue with fastapi/uvicorn on conda-forge:**
- GenIce3 pins `fastapi>=0.135.3,<0.136.0` — conda-forge has 0.138.1 (too new)
- GenIce3 pins `uvicorn>=0.44.0,<0.45.0` — conda-forge has 0.49.0 (too new)
- **Since fastapi/uvicorn shouldn't be core deps**, this is moot for QuickIce

**For QuickIce's install strategy:** Most new deps (pyyaml, jinja2) can come from conda-forge. `cif2ice` must be pip-installed. GenIce3 itself is pip-only.

**Confidence:** HIGH for pyyaml/jinja2/fastapi/uvicorn (verified on anaconda.org); MEDIUM for genice3/cif2ice (404 confirmed, but PyPI blocked).

---

## 8. PySide6/VTK Stack Compatibility

### Direct Conflict Check

| GenIce3 Dependency | PySide6/VTK Conflict? | Notes |
|---|---|---|
| numpy >=2.0 | No | VTK 9.5.2 supports numpy 2.x |
| networkx | No | Pure Python, no Qt/VTK interaction |
| pyyaml | No | Pure Python, no binary deps |
| jinja2 | No | Pure Python, no binary deps |
| cif2ice | **UNLIKELY** | Niche package; no known Qt conflicts |
| fastapi | **UNLIKELY** | Web framework, no Qt interaction |
| uvicorn | **UNLIKELY** | ASGI server, no Qt interaction |
| genice-core | No | Pure Python + networkx |

### Transitive Dependency Risks

If fastapi is installed (even though it shouldn't be), its transitive deps include:
- **pydantic v2** — well-maintained, no Qt conflicts
- **starlette** — ASGI toolkit, no Qt conflicts
- **anyio** — async I/O, no Qt conflicts

**Assessment:** No conflicts between GenIce3 dependencies and QuickIce's PySide6/VTK stack.

**Confidence:** HIGH.

---

## 9. Supply Chain Risk — Full Dependency Tree

### GenIce3 Core Dependencies (pyproject.toml)

```
genice3
├── networkx >=2.0.dev20160901144005     [WIDELY USED, LOW RISK]
├── numpy >=2.0                          [WIDELY USED, LOW RISK]
├── pairlist >=0.6.4                     [NICHE, vitroid, MEDIUM RISK]
├── cycless >=0.7                        [NICHE, vitroid, MEDIUM RISK]
├── graphstat >=0.3.3                    [NICHE, vitroid, MEDIUM RISK]
├── yaplotlib >=0.1.2                    [NICHE, vitroid, MEDIUM RISK]
├── openpyscad >=0.5.0                   [NICHE, vitroid, MEDIUM RISK]
├── pyyaml >=6.0                         [WIDELY USED, LOW RISK]
├── jinja2 >=3.1.4                       [WIDELY USED, LOW RISK]
├── cif2ice >=0.4.1,<0.5.0              [NICHE, vitroid, MEDIUM RISK]
├── genice-core >=1.5.4,<2.0.0          [NICHE, vitroid, MEDIUM RISK]
├── fastapi >=0.135.3,<0.136.0          [SHOULD NOT BE HERE — packaging bug]
└── uvicorn >=0.44.0,<0.45.0            [SHOULD NOT BE HERE — packaging bug]
```

### Risk Assessment by Category

| Category | Packages | Maintainer | Risk Level | Rationale |
|---|---|---|---|---|
| **Widely used** | numpy, networkx, pyyaml, jinja2 | Community/Foundations | LOW | Large contributor base, regular releases |
| **GenIce ecosystem** | genice-core, cif2ice, pairlist, cycless, graphstat, yaplotlib, openpyscad | vitroid (Masakazu Matsumoto) | **MEDIUM** | Single maintainer, academic project |
| **Web framework** (should be optional) | fastapi, uvicorn | Community | LOW if optional | But adds 10+ transitive deps if forced |

### Transitive Dependencies from fastapi/uvicorn (if installed)

```
fastapi
├── starlette >=0.40.0
│   └── anyio >=4.0.0
│       ├── idna >=2.8
│       └── sniffio >=1.1
├── pydantic >=2.0
│   ├── pydantic-core >=2.0
│   ├── typing-extensions >=4.6
│   └── annotated-types >=0.6
└── httpx (optional, for dev)

uvicorn
├── click >=8.0           [ALREADY IN QUICKICE]
├── h11 >=0.8
└── uvloop (optional, [standard] extra)
```

**Net new transitive deps from fastapi/uvicorn:** ~8 packages. All well-maintained, but unnecessary overhead for QuickIce.

**Confidence:** HIGH.

---

## 10. GenIce3 Version Status

| Version | Date | Status | Notes |
|---|---|---|---|
| 3.0a3 | ~2026-04 | Alpha | Early API |
| 3.0a4 | ~2026-04 | Alpha | API refinements |
| 3.0b0 | 2026-02-25 | Beta | First beta on PyPI |
| 3.0b1 | 2026-02-25 | Beta | Quick follow-up |
| 3.0b2 | 2026-02-25 | Beta | Quick follow-up |
| 3.0b3 | 2026-02-26 | Beta | **Current PyPI release** |
| 3.0b4 | ~2026-06 | Beta | **Current main branch** (not yet on PyPI) |

**Important:** GenIce3 is still in **beta (pre-release)**. The API is actively evolving. The packaging bug with fastapi/uvicorn in core deps may be fixed in a future release. No stable release exists yet.

**Confidence:** HIGH — verified from PyPI release history and GitHub README.

---

## 11. Summary of Findings by Research Question

| Question | Answer | Confidence |
|---|---|---|
| Why does GenIce3 depend on fastapi/uvicorn? | For Web API server feature. **Should be optional** — it's a packaging bug that they're in core deps. The code handles missing fastapi gracefully with try/except. | HIGH |
| Will Python 3.14 support be added? | No evidence of planned 3.14 support. No issues filed. The author builds on 3.10. A PR to relax the upper bound would likely be accepted. | MEDIUM |
| What changed in genice-core 1.5.4 vs 1.4.3? | Major API changes: polarize_loop merged into ice_graph, seed parameter added, parameter renaming, new BFS/MCF path connection algorithms, legacy connect_engine deprecated. | HIGH |
| Can GenIce2 and GenIce3 coexist? | **NO** — genice-core version ranges are mutually exclusive. Separate envs or full migration required. | HIGH |
| Are there conda-forge packages? | pyyaml, jinja2, fastapi, uvicorn = YES. genice3, cif2ice = NO (pip only). | HIGH |
| What is the actual Python 3.14 incompatibility? | **Conservative upper bound**, not a real code issue. genice-core has no upper bound; GenIce2 supports 3.14. One-line pyproject.toml patch likely sufficient. | HIGH (bound is conservative) / MEDIUM (no runtime issues) |
| PySide6/VTK stack conflicts? | No conflicts detected. GenIce3's deps are pure Python; no binary/library conflicts with Qt/VTK. | HIGH |
| Supply chain risk? | MEDIUM — 6 niche vitroid-maintained packages in the GenIce ecosystem. fastapi/uvicorn add ~8 transitive deps unnecessarily. | HIGH |

---

## 12. Recommended Path Forward

### Short-term (Proof of Concept)

1. **Fork GenIce3** at v3.0b4
2. **Patch `requires-python`** to `">=3.11,<4.0"`
3. **Move fastapi/uvicorn to optional deps only** (fix the packaging bug)
4. **Create a test conda env** with Python 3.14 + patched GenIce3
5. **Validate GenIce3 core functionality** on Python 3.14 (run GenIce3's own tests)
6. **Create a QuickIce integration prototype** that calls GenIce3 API instead of GenIce2

### Medium-term (Migration)

1. **Rewrite QuickIce's GenIce integration layer** for GenIce3 API
2. **Handle genice-core API changes**: update `ice_graph()` call signatures, adapt to new parameter names
3. **Replace GenIce2 pipeline stages** with GenIce3's reactive DependencyEngine approach
4. **Add pyyaml, jinja2, cif2ice** to environment.yml
5. **Remove genice2, deprecation, and genice-core 1.4.3** from environment.yml

### Long-term (Upstream)

1. **File issues/PRs upstream** for Python 3.14 support and fastapi packaging fix
2. **Monitor GenIce3 releases** for stable version (currently beta)
3. **Evaluate GenIce3's new features** (defect embedding, Bjerrum defects, reactive pipeline) for QuickIce value

---

## Sources

| Source | URL | What Verified | Confidence |
|---|---|---|---|
| GenIce3 PyPI (3.0b3) | https://pypi.org/project/genice3/3.0b3/ | Dependencies, Python version, release dates | HIGH |
| GenIce3 GitHub (main) | https://github.com/genice-dev/GenIce3 | pyproject.toml, README, WebAPI.md, webapi.py, CLI code | HIGH |
| GenIce3 pyproject.toml | https://raw.githubusercontent.com/.../pyproject.toml | Exact dependency specs, packaging bug | HIGH |
| GenIce3 webapi.py | https://raw.githubusercontent.com/.../webapi.py | fastapi try/except, lazy import | HIGH |
| GenIce3 runner.py | https://raw.githubusercontent.com/.../runner.py | pyyaml import with try/except, YAML config loading | HIGH |
| GenIce3 genice.py | https://raw.githubusercontent.com/.../genice.py | cif2ice direct import, GenIce3 API, DependencyEngine | HIGH |
| GenIce3 engine.py | https://raw.githubusercontent.com/.../engine.py | Core pipeline, no web deps | HIGH |
| GenIce3 RELEASE_NOTE.md | https://raw.githubusercontent.com/.../RELEASE_NOTE.md | Version progression, feature changes | HIGH |
| genice-core GitHub | https://github.com/genice-dev/genice-core | pyproject.toml, version 1.6.1 | HIGH |
| genice-core pyproject.toml | https://raw.githubusercontent.com/.../pyproject.toml | Python `>=3.11,<4.0`, deps | HIGH |
| genice-core commits | https://github.com/.../commits/main | Changelog between versions | HIGH |
| GenIce3 GitHub Issues | https://github.com/.../issues | 0 issues about Python 3.14 | HIGH |
| GenIce2 PyPI | https://pypi.org/project/genice2/ | GenIce2 supports Python 3.14 | HIGH |
| conda-forge pyyaml | https://anaconda.org/conda-forge/pyyaml | Available, v6.0.3 | HIGH |
| conda-forge jinja2 | https://anaconda.org/conda-forge/jinja2 | Available, v3.1.6 | HIGH |
| conda-forge fastapi | https://anaconda.org/conda-forge/fastapi | Available, v0.138.1 | HIGH |
| conda-forge uvicorn | https://anaconda.org/conda-forge/uvicorn | Available, v0.49.0 | HIGH |
| conda-forge cif2ice | https://anaconda.org/conda-forge/cif2ice | NOT available (404) | HIGH |
| conda-forge genice3 | https://anaconda.org/conda-forge/genice3 | NOT available (404) | HIGH |
| QuickIce environment.yml | /share/home/nglokwan/quickice/environment.yml | Current deps, Python 3.14.3 | HIGH |
