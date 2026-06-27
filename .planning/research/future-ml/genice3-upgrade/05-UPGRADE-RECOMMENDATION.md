# GenIce3 Upgrade Recommendation

**Project:** QuickIce GenIce3 Upgrade Assessment
**Date:** 2026-06-27
**Verdict:** GO LATER — upgrade when GenIce3 reaches stable release + Python 3.14 support
**Confidence:** HIGH

---

## 1. Executive Summary

**Do not upgrade to GenIce3 now.** GenIce3 (3.0b3 on PyPI, 3.0b4 on GitHub main) is beta software with two hard blockers: Python 3.14 incompatibility and genice-core version conflict. No stable release exists, no release timeline has been announced, and the project has minimal community traction (2 GitHub stars, 0 forks, 0 open issues). However, **upgrading is the correct long-term direction** — GenIce3's features (TIP4P/Ice direct generation, CIF input, spot ions, cage survey JSON) are genuinely valuable for QuickIce, and the migration path is well-understood and mechanically straightforward.

**The recommended strategy is proactive waiting:** continue with GenIce2 while immediately engaging upstream to resolve the Python 3.14 blocker and packaging bugs. Create a prototype migration branch to validate the API changes. When GenIce3 3.0.0 ships with Python 3.14 support, execute the migration in one clean cutover.

**Timeline estimate:** 3–6 months to stable release (speculative, no official timeline). Migration execution: 1–2 weeks of focused dev work once blockers clear.

**Why not now:**
- Beta API may change before stable — any work now risks throwaway effort
- Python 3.14 bound requires patching (fork or local) — adds ongoing maintenance
- fastapi/uvicorn packaging bug adds unnecessary dependency weight
- GenIce2 is still maintained (v2.2.13.3 released March 2026) — no urgency

**Why not never:**
- GenIce2's genice-core is pinned `<1.3` — it may not receive further algorithm updates
- GenIce3's TIP4P/Ice direct generation eliminates our 3→4 atom normalization hack
- CIF input, spot ions, and cage survey JSON are high-value features for QuickIce's roadmap
- GenIce2 is "completed" per its README — the author's active development is on GenIce3

---

## 2. Decision Matrix

Each scenario evaluated against seven criteria. Ratings: ✓ (favorable), ~ (mixed), ✗ (unfavorable).

| Criterion | A: Upgrade Now | B: Wait for Stable | C: Never Upgrade | D: Hybrid/Adapter |
|-----------|:-:|:-:|:-:|:-:|
| **Python 3.14 compatibility** | ✗ (must patch) | ✓ (upstream fix expected) | ✓ (GenIce2 works) | ✗ (both envs needed) |
| **Beta API stability** | ✗ (may change) | ✓ (stable = locked API) | ✓ (GenIce2 stable) | ~ (GenIce2 stable, GenIce3 not) |
| **Feature access** | ✓ (all GenIce3 features) | ✓ (eventually all) | ✗ (no new features) | ~ (GenIce3 opt-in only) |
| **Maintenance burden** | ✗ (fork + re-patch) | ✓ (upstream handles it) | ✓ (no change) | ✗ (dual maintenance) |
| **Migration effort** | ✓ (do it once) | ~ (deferred but same effort) | ✓ (no effort) | ✗ (adapter layer + both APIs) |
| **Scientific correctness** | ✓ (TIP4P/Ice direct) | ~ (eventually) | ~ (normalization works but is hack) | ~ (GenIce3 path more correct) |
| **Coexistence feasibility** | ✗ (genice-core conflict) | ✓ (clean cutover) | ✓ (no change) | ✗ (requires separate envs) |
| **Overall** | **2/7** | **6/7** | **4/7** | **0.5/7** |

### Scenario A: Upgrade Now (despite blockers)

**What it requires:**
1. Fork GenIce3 at v3.0b4
2. Patch `requires-python` from `<3.14` to `<4.0` (one-line change in pyproject.toml)
3. Move fastapi/uvicorn from core deps to `[web]` extras only
4. Install patched GenIce3 + genice-core ≥1.5.4 in QuickIce's Python 3.14 environment
5. Rewrite `generator.py` and `hydrate_generator.py` for GenIce3 API
6. Update environment.yml, tests, GUI text

**Estimated effort:** 1–2 weeks of focused dev work

**Why rejected:**
- Beta API may change — any migration work risks being invalidated by a 3.0.0 release with API tweaks
- Fork maintenance burden: every GenIce3 update requires re-patching pyproject.toml
- fastapi/uvicorn packaging bug should be fixed upstream, not worked around
- GenIce3 has no community validation (2 stars, 0 forks) — we'd be an early adopter on a beta
- If we discover a GenIce3 bug, we're on our own — no community, no issue history

### Scenario B: Upgrade When Stable (RECOMMENDED)

**What it requires:**
1. Continue with GenIce2 in production
2. File Python 3.14 support issue on GenIce3 GitHub NOW
3. File fastapi/uvicorn packaging bug issue on GenIce3 GitHub NOW
4. Optionally submit PRs for both issues (trivial fixes)
5. Create a prototype migration branch (not merged) to validate API changes
6. Monitor GenIce3 releases for 3.0.0 stable
7. When stable + Python 3.14 support: execute full migration

**Estimated effort:** 2–3 days for upstream engagement now; 1–2 weeks for migration later

**Why recommended:**
- No ongoing fork maintenance — upstream fixes the blockers
- Clean cutover from GenIce2 to GenIce3 (no adapter layer needed)
- Stable API = migration work is not throwaway
- GenIce2 remains functional — no disruption to current users
- Proactive upstream engagement accelerates the timeline
- The API migration is well-understood — see 01-API-MIGRATION-MAP.md

### Scenario C: Never Upgrade

**What it requires:**
1. Stay on GenIce2 indefinitely
2. Accept that genice-core 1.2.x may not receive further updates
3. Accept feature gap (no TIP4P/Ice direct, no CIF, no spot ions, no cage survey JSON)
4. Risk: if Python 3.15+ breaks GenIce2 or genice-core 1.2.x, we're stuck

**Why rejected for long-term:**
- GenIce2 is "completed" software — the author's active work is GenIce3
- genice-core `<1.3` means no algorithm improvements (the 1.5.4+ BFS/MCF algorithms are faster and better)
- Missing features are genuinely valuable — CIF input and spot ions expand QuickIce's capabilities
- The 3→4 atom TIP3P→TIP4P-ICE normalization is a hack that GenIce3 eliminates entirely
- Growing divergence from upstream makes eventual migration harder, not easier

**Partial acceptance:** Staying on GenIce2 is fine for the next 3–6 months. The rejection is of "never" as a permanent strategy.

### Scenario D: Hybrid / Adapter Layer

**What it requires:**
1. Write an abstraction layer that supports both GenIce2 and GenIce3
2. Runtime detection of which library is available
3. Separate code paths for each API
4. Deal with the genice-core conflict via separate Python environments or subprocess isolation

**Why rejected:**
- **genice-core conflict makes coexistence impossible in one environment** — the adapter layer would need subprocess isolation or separate conda envs, adding complexity for marginal benefit
- The API surface is different enough (inverted call pattern, parameter locations, guest syntax) that the adapter would be complex
- Dual code paths mean dual test maintenance
- QuickIce only uses GenIce in 2 files — the adapter layer would be MORE code than just migrating
- If we're going to maintain GenIce3 support, we should just fully commit to it

---

## 3. Recommended Pathway

### Phase 0: Upstream Engagement (NOW — 1–2 days)

**Goal:** Resolve blockers upstream so stable GenIce3 works on Python 3.14

| Action | What | Why | Effort |
|--------|------|-----|--------|
| File Python 3.14 issue | Open GitHub issue on genice-dev/GenIce3 requesting `<3.14` bound be relaxed to `<4.0` | genice-core already has no upper bound; GenIce2 supports 3.14; bound appears conservative | 15 min |
| File packaging bug issue | Open GitHub issue noting fastapi/uvicorn in core deps when `[web]` extras exist | Both deps have try/except ImportError; web code is separate; clearly a packaging error | 15 min |
| Submit PR for Python bound | Change `requires-python = ">=3.11,<3.14"` to `">=3.11,<4.0"` in pyproject.toml | One-line fix; low risk; builds goodwill with maintainer | 30 min |
| Submit PR for packaging bug | Move fastapi/uvicorn from `dependencies` to `[project.optional-dependencies] web` | Trivial fix; reduces unnecessary deps for library users | 30 min |
| Contact maintainer | Email vitroid@gmail.com expressing interest in GenIce3 stable + Python 3.14 | Shows community demand; may accelerate stable release timeline | 15 min |

**If the maintainer is responsive** (likely — academic projects often welcome patches), the Python 3.14 and packaging blockers could be resolved within days.

**If the maintainer is unresponsive**, we still have options:
- Fork GenIce3 with the patches ourselves (this is Scenario A with less uncertainty)
- Wait for community adoption to push the maintainer

### Phase 1: Prototype Migration Branch (1–2 weeks, parallel with Phase 0)

**Goal:** Validate the API migration map on a non-production branch

1. Create a fork of GenIce3 with Python 3.14 patch + packaging fix
2. Install in a test conda env: `pip install -e .` from patched source
3. Create `genice3-migration` branch in QuickIce
4. Rewrite `generator.py` `_generate_single()` for GenIce3 API
5. Rewrite `hydrate_generator.py` `_run_via_api()` for GenIce3 API
6. Update `mapper.py` lattice name mappings if needed
7. Update `environment.yml` (remove genice2, add genice3 + pyyaml + jinja2 + cif2ice)
8. Run existing test suite — verify GRO output matches GenIce2 baseline
9. **DO NOT MERGE** — this is a validation branch only

**Success criteria for prototype:**
- All ice phases (Ih, Ic, II, III, V, VI, VII, VIII) generate identical GRO output as GenIce2
- All hydrate phases (sI, sII, sH) generate identical GRO output as GenIce2
- `water_model="ice"` produces correct TIP4P-ICE geometry (compare with normalization output)
- Thread safety is preserved (np.random save/restore still needed)
- Test suite passes with GenIce3 backend

**Risk:** If the prototype reveals API inconsistencies not covered in the migration map, we learn early and can file issues upstream.

### Phase 2: Wait for Stable Release (3–6 months, estimated)

**Conditions that must be true before migration:**

| # | Condition | Why Required | How to Verify | Confidence |
|---|-----------|-------------|----------------|------------|
| C1 | GenIce3 3.0.0 (stable) released on PyPI | API locked; no breaking changes after stable | Check PyPI release history | MEDIUM — no official timeline |
| C2 | Python 3.14 support (either upstream or in our fork) | QuickIce runs Python 3.14.3 | Check `requires-python` in pyproject.toml | HIGH — one-line fix, genice-core already supports it |
| C3 | fastapi/uvicorn moved to optional deps | Avoid unnecessary web framework deps | Check pyproject.toml dependencies | HIGH — clear packaging bug |
| C4 | Prototype migration branch validated | Prove migration is mechanically straightforward | All tests pass on migration branch | HIGH — API map is complete |
| C5 | GRO output format stability confirmed | GRO parsing must work unchanged | Diff GRO output between GenIce2 and GenIce3 for all phases | HIGH — format already verified identical |

**If C1 (stable release) never materializes:**
- Reassess at 6-month mark
- If GenIce3 GitHub is still active but no stable release, consider forking with patches and using 3.0b4 as "our stable"
- If GenIce3 GitHub goes inactive, stay on GenIce2 indefinitely

### Phase 3: Production Migration (1–2 weeks, once conditions met)

**Detailed migration plan:**

| Step | File(s) | Change | Effort | Risk |
|------|---------|--------|--------|------|
| 1 | `environment.yml` | Replace `genice2=2.2.13.1` + `genice-core=1.4.3` with `genice3>=3.0.0` + `pyyaml>=6.0` + `jinja2>=3.1.4` + `cif2ice>=0.4.1`. Remove `deprecation=2.1.0`. | 15 min | LOW |
| 2 | `quickice/structure_generation/generator.py` | Replace GenIce2 imports/API with GenIce3. Use `GenIce3(seed=seed, pol_loop_1=2000, replication_matrix=M)` + `set_unitcell(name, density=d)` + `Exporter("gromacs").dumps(genice, water_model="3site")`. Keep np.random save/restore. | 2 hours | LOW — exact API documented |
| 3 | `quickice/structure_generation/hydrate_generator.py` | Replace GenIce2 imports/API with GenIce3. Use `parse_guest_option({"A12": "ch4", "A14": "ch4"})`. Add "A" prefix to cage names. Use `water_model="4site"` or `"ice"`. | 3 hours | MEDIUM — sH cage naming needs verification |
| 4 | `quickice/structure_generation/mapper.py` | Verify all lattice name mappings still valid (all QuickIce names exist in GenIce3 per 01-API-MIGRATION-MAP.md §2.4). May add GenIce3-only aliases. | 30 min | LOW |
| 5 | `quickice/structure_generation/gro_parser.py` | No changes needed — GRO format is identical between GenIce2 and GenIce3. | 0 | NONE |
| 6 | Test fixtures (`tests/conftest.py`, etc.) | Update any test code that directly imports `genice2` modules. | 1 hour | LOW |
| 7 | `quickice-gui.spec` (PyInstaller) | Update hiddenimports from `genice2.*` to `genice3.*`. | 30 min | LOW |
| 8 | **Optional:** Use `water_model="ice"` for hydrates | Switch from TIP3P + normalization to direct TIP4P-ICE. Remove normalization code in `generator.py`. Update GRO parsing expectations (4 atoms from start). | 4 hours | MEDIUM — must verify MW position matches |
| 9 | Integration testing | Run full test suite + GROMACS grompp validation on all phase outputs. | 2 hours | LOW |
| 10 | Documentation updates | Update references from GenIce2 to GenIce3 in code comments, README, etc. | 1 hour | NONE |

**Total estimated effort:** ~14 hours (1.5–2 working days) for core migration; ~4 additional hours if switching to `water_model="ice"` for hydrates.

---

## 4. Conditions for Upgrade

### Mandatory conditions (all must be met):

| # | Condition | Rationale | Timeline |
|---|-----------|-----------|----------|
| M1 | GenIce3 stable (3.0.0) released | Prevents API-breaking changes; beta API is not contractually stable | Unknown — no official timeline. 3–6 months estimate. |
| M2 | Python 3.14 installable | QuickIce's environment is Python 3.14.3; cannot downgrade | Trivial one-line fix upstream; also achievable via fork |
| M3 | genice-core conflict resolved | GenIce2 and GenIce3 cannot coexist; clean cutover required | Resolved by full migration (no coexistence needed) |

### Strongly recommended conditions:

| # | Condition | Rationale | Timeline |
|---|-----------|-----------|----------|
| R1 | fastapi/uvicorn moved to optional deps | Avoids ~8 unnecessary transitive dependencies | Trivial packaging fix; likely before stable |
| R2 | Prototype migration validated | Proves migration is straightforward before committing | Can do now on separate branch |
| R3 | sH cage naming verified | Hydrate generation for sH needs correct cage labels ("A20" for large cage?) | Run cage_survey exporter on sH |
| R4 | ice1h axis convention verified | GenIce3 warns about historical axis swap; must confirm GenIce2 compatibility | Compare GRO box vectors |

### Nice-to-have conditions:

| # | Condition | Rationale | Timeline |
|---|-----------|-----------|----------|
| N1 | GenIce3 community validation (>10 stars, >5 forks) | Indicates other users have tested; bug surface exposed | Organic growth |
| N2 | Published performance benchmarks | Confirm no regression vs GenIce2 | Depends on maintainer |
| N3 | conda-forge package available | Simplifies QuickIce installation (all deps from conda-forge) | Community contribution |

---

## 5. Risk Register

### Critical Risks

| ID | Risk | Likelihood | Impact | Mitigation | Residual |
|----|------|-----------|--------|------------|----------|
| CR-1 | GenIce3 stable release never ships | LOW | HIGH — stuck on GenIce2 indefinitely | Engage upstream; fork if needed; GenIce2 is functional | MEDIUM |
| CR-2 | GenIce3 has Python 3.14 runtime bugs (despite passing install) | LOW | HIGH — crashes in production | Prototype migration on Python 3.14; run GenIce3's own test suite on 3.14 | LOW |
| CR-3 | GenIce3 API breaks between beta and stable | MEDIUM | HIGH — prototype work wasted | Don't merge prototype; wait for stable before committing | LOW (if we wait) |
| CR-4 | genice-core API divergence from 1.4.x to 1.5.4+ causes subtle bugs | LOW | HIGH — wrong ice structures | Verify GRO output matches GenIce2 baseline for all phases | LOW |

### Moderate Risks

| ID | Risk | Likelihood | Impact | Mitigation | Residual |
|----|------|-----------|--------|------------|----------|
| MR-1 | GenIce3 maintainer unresponsive to Python 3.14 issue | MEDIUM | MEDIUM — must maintain fork | Fork with patch; re-patch on updates | MEDIUM |
| MR-2 | GenIce3 beta has undiscovered bugs in rare code paths | MEDIUM | MEDIUM — incorrect structures in edge cases | Thorough integration testing; GROMACS grompp validation | LOW |
| MR-3 | cif2ice dependency not available on conda-forge | HIGH | LOW — must pip install one extra package | Add pip install to setup.sh; already handled by pip | LOW |
| MR-4 | sH hydrate cage naming wrong in migration | MEDIUM | MEDIUM — wrong guest placement for sH | Verify with cage_survey exporter; add regression test | LOW |
| MR-5 | Thread safety issue with np.random.seed in GenIce3 | LOW | MEDIUM — race conditions in GUI | Keep existing np.random save/restore pattern; no change | LOW |

### Minor Risks

| ID | Risk | Likelihood | Impact | Mitigation | Residual |
|----|------|-----------|--------|------------|----------|
| LR-1 | GenIce3 adds breaking API changes after 3.0.0 stable | LOW | LOW — standard semver risk | Pin `genice3>=3.0.0,<4.0.0` in environment.yml | LOW |
| LR-2 | GenIce2 removed from PyPI | VERY LOW | LOW — can't reinstall GenIce2 | GenIce2 is MIT licensed; mirror if needed | VERY LOW |
| LR-3 | New GenIce3 dependencies conflict with QuickIce stack | LOW | LOW — most are pure Python | Test installation in QuickIce env before migration | LOW |

---

## 6. Migration Plan Outline

### When Conditions Are Met (C1–C5 all true)

```
Week 1:
  Day 1-2: Core migration (Steps 1-6 from §3 Phase 3)
  Day 3:   Integration testing (Step 9)
  Day 4:   water_model="ice" migration (Step 8, optional)
  Day 5:   Documentation + PyInstaller (Steps 7, 10)

Week 2 (if needed):
  Day 1-2: Bug fixes from integration testing
  Day 3:   GROMACS grompp validation on all phases
  Day 4:   GUI testing (if applicable)
  Day 5:   Buffer / regression testing
```

### Rollback Plan

If GenIce3 migration encounters critical issues after merge:

1. Revert environment.yml to GenIce2 + genice-core 1.4.3
2. Revert generator.py and hydrate_generator.py to GenIce2 API
3. Re-run test suite on GenIce2 — should pass (GenIce2 is known-good)

The migration is structurally simple (2 main files + env) so rollback is straightforward.

### Post-Migration Opportunities

Once on GenIce3, these features become available:

| Feature | QuickIce Benefit | Implementation Effort |
|---------|-----------------|----------------------|
| `water_model="ice"` for all structures | Eliminate TIP3P→TIP4P-ICE normalization | 4 hours (already planned in migration Step 8) |
| CIF input as unit cell | Allow users to import any crystal structure | MEDIUM — new UI tab or file dialog |
| Spot ions (`-A`/`-C`) | Replace post-hoc ion insertion with GenIce-native doping | HIGH — replaces entire ion_inserter.py workflow |
| Cage survey JSON | Populate hydrate UI with cage types/positions | MEDIUM — new exporter integration |
| Ice XXI (21) | Extend phase coverage from 8 to 9 | LOW — add to mapper.py |
| Stacking disorder (`one`, `eleven`) | Realistic ice I with stacking faults | MEDIUM — new UI controls |

---

## 7. Upstream Action Items

### Immediate (do now — 30 minutes total)

| # | Action | Where | What to Say | Expected Response |
|---|--------|-------|-------------|-------------------|
| 1 | File Python 3.14 issue | github.com/genice-dev/GenIce3/issues | "GenIce3 requires `<3.14` but genice-core declares `<4.0` and GenIce2 supports 3.14. The bound appears conservative. Can it be relaxed?" | Likely acceptance — one-line fix with no risk |
| 2 | File packaging bug issue | github.com/genice-dev/GenIce3/issues | "fastapi and uvicorn are in core dependencies but should be in [web] extras only. webapi.py already has try/except ImportError for them." | Likely acceptance — clear bug |
| 3 | Submit PR for Python bound | github.com/genice-dev/GenIce3/pulls | Change `requires-python` from `">=3.11,<3.14"` to `">=3.11,<4.0"` | Trivial review; low risk merge |
| 4 | Submit PR for packaging fix | github.com/genice-dev/GenIce3/pulls | Move fastapi/uvicorn from `dependencies` to `[project.optional-dependencies] web` | Trivial review; fixes a clear error |

### Optional (if maintainer is responsive)

| # | Action | Where | What to Say |
|---|--------|-------|-------------|
| 5 | Request stable release timeline | Email vitroid@gmail.com | "We'd like to migrate QuickIce to GenIce3. Is there a timeline for 3.0.0 stable? We've filed Python 3.14 and packaging PRs." |
| 6 | Request sH cage naming documentation | GitHub issue or email | "What are the correct GenIce3 cage labels for sH hydrate's three cage types?" |
| 7 | Request ice1h axis convention clarification | GitHub issue or email | "Does GenIce3's `ice1h` use the same historical (swapped) axis convention as GenIce2? Or should we use `ice1h_unit`?" |

### Contributing back (during/after migration)

| # | Action | What | Effort |
|---|--------|------|--------|
| 8 | Report any GenIce3 bugs found | File issues with reproduction steps | Variable |
| 9 | Share migration guide | Point GenIce3 docs to our migration map as a resource | 1 hour |
| 10 | Add conda-forge recipe | Create feedstock for genice3 + cif2ice on conda-forge | 2–4 hours |

---

## 8. Timeline Estimate

### Realistic Timeline

```
2026-06 (now)     ─── Phase 0: File upstream issues + PRs
2026-07           ─── Phase 1: Prototype migration branch (validation only)
2026-07 to 2026-12 ─── Phase 2: Wait for GenIce3 3.0.0 stable + Python 3.14 support
                       (Monitor PyPI + GitHub; ping maintainer monthly)
2026-Q3 or Q4     ─── Phase 3: Production migration (1–2 weeks once conditions met)
```

### Best Case (maintainer responsive, stable release soon)

```
2026-06      ─── Issues filed, PRs submitted
2026-07      ─── PRs merged, 3.0b5 or 3.0.0rc1 with Python 3.14 + packaging fix
2026-08      ─── 3.0.0 stable released
2026-08/09   ─── Migration executed
```

**Best-case timeline: 2–3 months from now.**

### Worst Case (maintainer unresponsive, no stable release)

```
2026-06      ─── Issues filed, no response
2026-09      ─── Reassess: fork GenIce3 with patches?
2026-12      ─── If still no response, consider fork as "our GenIce3"
2027         ─── If no stable release by 12 months, accept GenIce2 as permanent
```

**Worst-case: 6–12 months of uncertainty, then either fork or accept GenIce2.**

### Decision Points

| Date | Check | Decision |
|------|-------|----------|
| 2026-09 (3 months) | Has maintainer responded to issues? Any new GenIce3 release? | If NO response: escalate via email; consider forking |
| 2026-12 (6 months) | Is GenIce3 3.0.0 released or imminent? | If NO release but active development: continue waiting. If inactive: stay on GenIce2 permanently. |
| 2027-03 (9 months) | Final assessment | If no path to GenIce3, document GenIce2 as permanent backend |

---

## 9. Confidence Assessment

| Area | Confidence | Reason |
|------|------------|--------|
| API migration map (GenIce2→GenIce3) | **HIGH** | All 13 API calls mapped with working code examples; verified against official docs + source code |
| GRO output format compatibility | **HIGH** | Atom names, residue names, and column format verified identical from source code |
| Python 3.14 bound is conservative | **HIGH** | genice-core has no upper bound; GenIce2 supports 3.14; no known 3.14-breaking code in GenIce3 |
| genice-core conflict is real | **HIGH** | Verified from both packages' pyproject.toml; ranges are mutually exclusive |
| fastapi/uvicorn is packaging bug | **HIGH** | Code has try/except ImportError; [web] extras already defined; version pins inconsistent |
| Migration effort estimate (1–2 weeks) | **HIGH** | Only 2 main files + environment.yml; exact API changes documented |
| GenIce3 3.0.0 stable release timeline | **LOW** | No official timeline; beta pace slowing suggests approach to stable; purely speculative |
| Maintainer responsiveness | **MEDIUM** | Academic maintainer; likely responsive to bug reports; but no community signals yet (2 stars) |
| GenIce2 long-term viability | **MEDIUM** | Still maintained (2.2.13.3 released Mar 2026); but genice-core pinned to 1.2.x; "completed" status |
| sH cage naming in GenIce3 | **MEDIUM** | Not explicitly documented; needs cage_survey verification |
| Thread safety unchanged in GenIce3 | **MEDIUM** | Source confirms np.random.seed still global; but untested on 3.14 |
| water_model="ice" eliminates normalization | **MEDIUM** | GenIce3 produces correct TIP4P-ICE geometry per docs; but MW position difference (0.015 vs 0.01577 nm) needs empirical verification |

---

## 10. Final Verdict

### GO LATER — Upgrade to GenIce3 when stable + Python 3.14 compatible

**The upgrade is the right long-term move.** GenIce3's features directly address QuickIce's current limitations (TIP4P-ICE normalization hack, hardcoded phase list, unit-cell-only ion doping). The migration is mechanically straightforward — 2 files, well-understood API changes, identical GRO output. The ecosystem risk is manageable (single academic maintainer, but MIT license and we can fork if needed).

**The upgrade is the wrong move right now.** Beta software with no stable release, no community validation, a Python version blocker, and a packaging bug. There is no urgency — GenIce2 is functional and still maintained.

**What to do:**

1. **This week:** File the Python 3.14 issue and packaging bug issue on GenIce3 GitHub. Submit the trivial one-line PRs. This is 30 minutes of work that could resolve both blockers.

2. **This month:** Create a prototype migration branch. Validate the API changes on a patched GenIce3 fork. Run the test suite. This is 1–2 weeks of work that derisks the eventual migration.

3. **Ongoing:** Monitor GenIce3 releases. When 3.0.0 ships with Python 3.14 support (or when we decide to fork), execute the migration.

4. **Decision checkpoint:** September 2026 (3 months from now). If no maintainer response and no new release, reassess — fork GenIce3 or accept GenIce2 permanently.

**The key insight:** The GenIce3 upgrade is not a question of *whether* but *when*. The "when" depends on upstream, and we can influence it by filing issues and submitting PRs now. The migration itself is a known quantity — the research is done, the API map is complete, and the effort is bounded at 1–2 weeks.

---

## Sources

| Source | URL | Confidence | What Verified |
|--------|-----|------------|---------------|
| GenIce3 PyPI (3.0b3) | https://pypi.org/project/genice3/3.0b3/ | HIGH | Dependencies, Python constraint, release dates |
| GenIce3 GitHub (main, v3.0b4) | https://github.com/genice-dev/GenIce3 | HIGH | pyproject.toml, source code, fastapi packaging bug |
| GenIce3 GitHub Issues | https://github.com/genice-dev/GenIce3/issues | HIGH | 0 issues about Python 3.14; minimal community |
| GenIce3 GitHub Releases | https://github.com/genice-dev/GenIce3/releases | HIGH | Empty — no stable release |
| genice-core GitHub (v1.6.1) | https://github.com/genice-dev/genice-core | HIGH | Python `>=3.11,<4.0` (no 3.14 upper bound) |
| genice-core pyproject.toml | https://raw.githubusercontent.com/.../pyproject.toml | HIGH | Exact Python and dependency constraints |
| GenIce2 PyPI (v2.2.13.3) | https://pypi.org/project/genice2/ | HIGH | Still maintained, Python 3.14 in classifiers |
| Wave 1 Research: API Migration Map | `.planning/research/future-ml/genice3-upgrade/01-API-MIGRATION-MAP.md` | HIGH | Complete API mapping with code examples |
| Wave 1 Research: Dependency Compatibility | `.planning/research/future-ml/genice3-upgrade/02-DEPENDENCY-COMPATIBILITY.md` | HIGH | All blockers and conflicts documented |
| Wave 1 Research: New Features | `.planning/research/future-ml/genice3-upgrade/04-NEW-FEATURES.md` | HIGH | Feature inventory with QuickIce relevance |
| QuickIce Roadmap | `.planning/ROADMAP.md` | HIGH | Current milestone status, no GenIce3 upgrade planned yet |
