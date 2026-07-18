---
status: resolved
trigger: "Scancode Group 3: CRIT-04 (assert stripped by python -O) + SAFE-05 (--output path-traversal) in quickice/cli/pipeline.py. Two atomic commits."
created: 2026-07-17T00:00:00Z
updated: 2026-07-17T00:45:00Z
goal: find_and_fix
---

## Current Focus

hypothesis: BOTH root causes CONFIRMED and FIXED. CRIT-04 committed as 19612b3
(helper extraction, 4 tests, fires under -O). SAFE-05 committed as ff9c798
(strict containment check + test-infrastructure update to use <cwd>/tmp/, 4 tests).
All verification green. Two atomic commits with exact PLAN.md messages. DONE.
test: (completed — see Verification)
expecting: (met — 8 new tests pass, 30 test_cli_pipeline.py pass, 44 under -O, 229/232 broader sample with 3 pre-existing failures)
next_action: Archive debug file (optional); report ROOT CAUSE FOUND.

## Symptoms

CRIT-04:
  expected: A hydrate whose water+guest atom count != len(hydrate.positions) is
    rejected with a clear error, regardless of Python optimization level.
  actual: Under `python -O` / `PYTHONOPTIMIZE=1`, the `assert` at pipeline.py:901
    is stripped, so a mismatch is not detected and (per the plan) corrupted data
    could export silently.
  errors: None under -O (silent). Under normal Python, AssertionError (uncaught
    by the export step's `except (OSError, ValueError)` at :952, so it would
    propagate).
  reproduction: Run the hydrate atom-count check under `python -O` with a
    mismatched hydrate; observe no error.
  started: Present since the assert was written (pipeline.py:901).

SAFE-05:
  expected: `--output` pointing outside the working directory is rejected,
    consistent with the input-path checks.
  actual: `--output` is resolved (pipeline.py:137) but NOT checked for
    containment, while inputs ARE checked at :242-249 (CSV) and :494-509
    (custom gro/itp), and orchestrator.py:48-56 checks output. Inconsistent.
  errors: None — the gap is silent.
  reproduction: Run pipeline with `--output` outside cwd; accepted. Compare
    `--input`/`--custom-gro` outside cwd which is rejected.
  started: Present since the input checks were added without mirroring to output.

## Evidence

- timestamp: 2026-07-17T00:01
  checked: pipeline.py:901-904 (CRIT-04 assert)
  found: |
    `assert water_atom_count + guest_atom_count == len(hydrate.positions), \
        f"Atom count mismatch: water_atom_count({water_atom_count}) + " \
        f"guest_atom_count({guest_atom_count}) != " \
        f"total positions({len(hydrate.positions)})"`
    This is an `assert` (stripped by `python -O` / PYTHONOPTIMIZE=1). Confirmed
    `python -O` strips asserts in this env (`python -O -c "assert False"` →
    no error). ROOT CAUSE CONFIRMED for CRIT-04.
  implication: The check disappears under -O. Fix = replace with `if ...: raise ValueError(...)`.

- timestamp: 2026-07-17T00:02
  checked: pipeline.py:894-896 (how water_atom_count / guest_atom_count are computed)
  found: |
    Line 895: `water_atom_count = hydrate.water_count * WATER_ATOMS_PER_MOLECULE`
    Line 896: `guest_atom_count = len(hydrate.positions) - water_atom_count`
    Line 901 condition: `water_atom_count + guest_atom_count == len(hydrate.positions)`
    Substituting: `water + (len(positions) - water) == len(positions)` => always True.
    **THE CHECK IS A MATHEMATICAL TAUTOLOGY — it can NEVER fire on any real hydrate.**
    The comment at :898-900 claims it "catches bugs where water_count*4 does not match
    actual water atoms in positions", but the implemented check does NOT achieve that
    (guest_atom_count is DEFINED to make the identity hold). This is a SEPARATE, deeper
    finding not anticipated by RESEARCH.md/PLAN.md.
  implication: |
    (a) Converting assert→raise has ZERO runtime effect today (check never fires either way);
    the fix is purely defensive/forward-looking (survives -O for the day someone fixes the tautology).
    (b) The planned test "construct a deliberately mismatched hydrate wrapper" is INFEASIBLE —
    no real hydrate can make the condition false, because guest_atom_count is derived from
    len(positions) itself.

- timestamp: 2026-07-17T00:03
  checked: pipeline.py:869-955 (export step try/except structure)
  found: |
    The check at :901 is INSIDE `try:` (open at :869). The `except (OSError, ValueError)`
    at :952 catches ValueError, logs, and `return 1`. So a `raise ValueError` at :901 would
    be CAUGHT LOCALLY → `_run_export_step` returns 1, it does NOT propagate to main.py.
    (Note: an `AssertionError` is NOT caught by `except (OSError, ValueError)`, so the OLD
    assert, if it could fire, would propagate — but it can't, it's a tautology.)
  implication: |
    A test that drives `_run_export_step` with a forced mismatch would observe `return 1`
    (not a raised ValueError). The plan's "assert ValueError is raised" only works if the
    check is extracted into a unit testable helper, OR if the test asserts the return code.

- timestamp: 2026-07-17T00:04
  checked: pipeline.py:137-142 (SAFE-05 output path handling)
  found: |
    `output_path = Path(self.args.output).resolve(); output_path.mkdir(parents=True, exist_ok=True); self._output_dir = output_path`
    wrapped in `try/except OSError`. NO `is_relative_to(cwd)` check. ROOT CAUSE CONFIRMED for SAFE-05.
    main.py:189 has `except Exception as e: print(...); return 1` — so a `raise ValueError`
    from execute() (NOT caught locally, since this try only catches OSError) propagates to
    main.py and yields exit code 1 with a clear message. Fail-fast is preserved.
  implication: Add containment check after resolve(); raise ValueError (mirrors CSV check :242-249).

- timestamp: 2026-07-17T00:05
  checked: Input containment checks to mirror (pipeline.py:242-249, :494-509; orchestrator.py:48-56)
  found: |
    CSV check (:242-249): `resolved = path.resolve(); cwd = Path.cwd().resolve();
      if not resolved.is_relative_to(cwd): raise ValueError(f"Positions CSV path resolves
      outside working directory: {resolved} is not under {cwd}")`  -> RAISES ValueError.
    Custom gro/itp check (:494-509): same resolve+cwd+is_relative_to, but uses
      `report_progress(...)` + `return 1` (does NOT raise). INCONSISTENT with CSV check.
    orchestrator.py:48-56: `output_path = Path(output_dir).resolve(); allowed_base = Path.cwd().resolve();
      if not output_path.is_relative_to(allowed_base): raise ValueError(f"Security error: Output path
      must be within {allowed_base}. Got: {output_path}")` -> RAISES ValueError.
  implication: |
    The two input checks are themselves inconsistent (CSV raises; custom returns 1). The
    orchestrator (same output-dir concern) RAISES ValueError. The plan + objective mandate
    ValueError for SAFE-05. I will mirror the CSV/orchestrator style (raise ValueError with
    a detailed "--output path resolves outside working directory: {p} is not under {cwd}" message),
    placed inside the existing try at :136 (ValueError is not OSError, so it propagates to main.py
    for fail-fast — consistent with CSV check behavior).

- timestamp: 2026-07-17T00:06
  checked: environment — gmx availability, python version, python -O behavior
  found: |
    `gmx` IS available: `/data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx`
    (GROMACS 2023.5-plumed_2.9.3). Python 3.14.3. `python -O -c "assert False"` → no error
    (assert stripped, confirmed). Path.is_relative_to available (3.9+).
  implication: gmx dry-run optional for these robustness fixes (not required). -O test feasible.

- timestamp: 2026-07-17T00:07
  checked: HydrateStructure type (types.py:1152-1189) for test-fixture design
  found: |
    `@dataclass class HydrateStructure`: fields positions(np.ndarray), atom_names(list[str]),
    cell(np.ndarray), molecule_index(list[MoleculeIndex), config, lattice_info, report(str),
    guest_count(int), water_count(int), guest_name, guest_atom_labels, guest_atom_count(int=0),
    guest_itp_path, guest_descriptors. Constructible directly for tests.
  implication: A test hydrate can be built via HydrateStructure(...) or SimpleNamespace for the
  shifty-len approach; but see tautology finding — a real mismatch cannot be constructed.

- timestamp: 2026-07-17T00:20
  checked: CRIT-04 fix applied + tested + committed
  found: |
    Applied Option B: extracted `_validate_hydrate_atom_counts(water_atom_count,
    guest_atom_count, total_positions) -> None` helper (raises ValueError on mismatch) at
    pipeline.py:33-55; replaced inline assert at :923-931 with a call to it. Added
    tests/test_scancode_bugs_pipeline.py with 4 CRIT-04 tests (helper raises on real mismatch,
    helper passes on consistent counts, check fires under `python -O` via subprocess,
    source-level AST guard that check site uses helper not assert). All 4 pass.
    `python -O -m pytest -k pipeline` confirms the 4 CRIT-04 tests pass under -O.
    Committed as 19612b3 "fix(scancode): replace stripped assert with ValueError in pipeline (CRIT-04)".
  implication: CRIT-04 fully resolved (fix + tests + commit).

- timestamp: 2026-07-17T00:25
  checked: SAFE-05 fix applied + tested
  found: |
    Applied SAFE-05: added containment check at pipeline.py:163-175 (after resolve, before mkdir):
    `cwd = Path.cwd().resolve(); if not output_path.is_relative_to(cwd): raise ValueError(...)`.
    Mirrors CSV check style. Added 4 SAFE-05 tests (out-of-cwd raises, traversal raises,
    in-cwd passes, absolute-in-cwd passes). All 4 pass. Verified tests are genuine regression
    tests (stash fix → 2 outside-cwd tests fail with "DID NOT RAISE"). Committed as 099250c.
  implication: SAFE-05 fix+test pass in isolation.

- timestamp: 2026-07-17T00:30
  checked: REGRESSION — SAFE-05 fix breaks 20 existing tests in test_cli_pipeline.py
  found: |
    Running `python -m pytest tests/test_cli_pipeline.py` WITH the SAFE-05 fix:
    20 failed, 10 passed. WITHOUT the fix (pre-fix code): 30 passed.
    The 20 failing tests all use `make_temp_output_dir()` (test_cli_pipeline.py:36-42)
    which calls `tempfile.mkdtemp(prefix="test_cli_pipeline_")` → creates dirs under
    the SYSTEM temp dir (/tmp/...), which is OUTSIDE the repo cwd (pytest runs from
    repo root). My SAFE-05 check correctly rejects these (per the input-check pattern),
    but this BREAKS the existing test pattern.
    The input checks at :242-249 (CSV) and :494-509 (custom-gro) do NOT break existing
    tests because the tests use IN-repo fixtures (e.g. ETOH_GRO = repo/data/custom/etoh.gro
    at test_cli_pipeline.py:32, which IS under cwd). So there is an ASYMMETRY: input
    fixtures live in-repo, but output dirs use system /tmp.
    `run_quickice` (conftest.py:222-247) runs `python -m quickice` as a subprocess with
    cwd = repo root; the --output arg is the /tmp path → rejected by SAFE-05.
    This regression happens WITHOUT -O too (not an optimization artifact).
  implication: |
    The SAFE-05 fix as specified (mirror input checks, reject out-of-cwd outputs) is
    INCOMPATIBLE with the existing test suite's use of /tmp output dirs. Returned
    CHECKPOINT; user chose Option B variant (keep strict check, move test dirs to <cwd>/tmp/).

- timestamp: 2026-07-17T00:40
  checked: SAFE-05 reconciliation — test-infrastructure fix
  found: |
    User chose Option B variant. Since 099250c was HEAD and unpushed, used
    `git reset --soft HEAD~1` to undo the SAFE-05 commit (keep changes staged),
    then applied the test-infrastructure fix:
    - Updated `make_temp_output_dir()` (tests/test_cli_pipeline.py:36-50) to create
      dirs under `<cwd>/tmp/` via `tempfile.mkdtemp(prefix="test_cli_pipeline_",
      dir=str(Path.cwd() / "tmp"))` after `tmp_base.mkdir(parents=True, exist_ok=True)`.
      Preserves the existing `shutil.rmtree(outdir, ignore_errors=True)` cleanup
      (each test removes only its own subdir, not the `tmp/` parent).
    - `.gitignore` ALREADY has `tmp/` at line 211 (under `#tmp` at :210) — verified
      via `git check-ignore -v tmp/placeholder.txt` → `.gitignore:211:tmp/`. No
      `.gitignore` edit needed.
    - No tracked files under `tmp/` (`git ls-files tmp/` empty).
    - The 20 callers of make_temp_output_dir() Just Work with no per-test changes.
    Re-committed as a SINGLE SAFE-05 commit ff9c798 (pipeline check + test fix +
    SAFE-05 tests), message exactly "fix(scancode): validate --output stays within
    cwd (SAFE-05)". CRIT-04 commit 19612b3 unchanged.
  implication: |
    Regression resolved. Strict SAFE-05 check preserved. Single clean commit.

## Eliminated

- hypothesis: "SAFE-05 fix must be relaxed to a warning to avoid breaking tests"
  evidence: User chose Option B variant — keep strict check, move test output dirs
  under <cwd>/tmp/. Verified all 30 test_cli_pipeline.py tests pass with the test
  fix. Strict check survives; no relaxation needed.
  timestamp: 2026-07-17T00:40

## Resolution

root_cause: |
  CRIT-04: pipeline.py:901 used `assert` (stripped by `python -O`/PYTHONOPTIMIZE=1)
  for runtime validation of hydrate atom counts.
  SAFE-05: pipeline.py:137 resolved `--output` without a containment check, while
  inputs were checked at :242-249 (CSV) and :494-509 (custom gro/itp), and
  orchestrator.py:48-56 checked output — an inconsistency.
  ADDITIONAL FINDINGS (documented, out of scope for this fix):
  (a) The CRIT-04 check is a tautology (guest_atom_count = len(positions) - water,
  so the condition is always True); converting assert→raise has zero runtime effect
  today but survives -O for the day the tautology is later fixed.
  (b) The export step catches ValueError locally (return 1), which is why the
  extracted-helper approach (Option B) was chosen for the CRIT-04 test.
  (c) The SAFE-05 check (mirror input checks) broke 20 existing tests that used
  system /tmp for output; resolved by moving test output dirs under <cwd>/tmp/.
fix: |
  CRIT-04 (commit 19612b33, Option B): Extracted module-level helper
  `_validate_hydrate_atom_counts(water_atom_count, guest_atom_count, total_positions)
  -> None` at pipeline.py:33-55 (body = `if ...: raise ValueError(...)`). Replaced
  the inline `assert` at the hydrate export site (now :923-931) with a call to the
  helper. The raise survives `python -O`. Added 4 tests in
  tests/test_scancode_bugs_pipeline.py (TestCRIT04StrippedAssert): helper raises on
  real mismatch, helper passes on consistent counts, check fires under `python -O`
  (subprocess), source-level AST guard that the check site uses the helper not assert.
  SAFE-05 (commit ff9c7983): Added containment check at pipeline.py:163-175: after
  `output_path = Path(self.args.output).resolve()`, `cwd = Path.cwd().resolve();
  if not output_path.is_relative_to(cwd): raise ValueError(...)`. Mirrors the
  CSV/orchestrator style. ValueError propagates past local `except OSError` to main.py
  for fail-fast. Updated `make_temp_output_dir()` in tests/test_cli_pipeline.py:36-50
  to create dirs under `<cwd>/tmp/` (already gitignored at .gitignore:211) so the 20
  existing pipeline tests comply. Added 4 tests (TestSAFE05OutputPathContainment):
  out-of-cwd raises, traversal raises, in-cwd passes, absolute-in-cwd passes.
verification: |
  pytest tests/test_scancode_bugs_pipeline.py -v: 8 passed (4 CRIT-04 + 4 SAFE-05).
  pytest tests/test_cli_pipeline.py: 30 passed (no regression — was 20 failed before
  the test-infrastructure fix).
  python -O -m pytest -k pipeline: 44 passed (CRIT-04 check fires under -O via
  subprocess test; SAFE-05 unaffected by -O; the pytest warning confirms -O is active).
  Broader sample (232 tests: all scancode_bugs + cli + entry + 8 CLI-e2e export/chain
  files): 229 passed, 3 failed. The 3 failures are PRE-EXISTING and unrelated:
  (1) test_cli_integration::test_boundary_nmolecules_max — GenIce2 subprocess 10s
  timeout on --nmolecules 1000; (2) test_cli_integration::test_version_shows_version —
  asserts "4.5.0" but version is "4.7.0" (anticipated by objective); (3)
  test_entry_point::test_version_shows_version — same 4.5.0 vs 4.7.0 mismatch.
  Verified pre-existing by stashing all my changes and re-running: identical 3 failures.
  Zero new failures from my changes.
files_changed: |
  quickice/cli/pipeline.py (CRIT-04 helper + call site; SAFE-05 containment check)
  tests/test_scancode_bugs_pipeline.py (4 CRIT-04 + 4 SAFE-05 tests, NEW file)
  tests/test_cli_pipeline.py (make_temp_output_dir now uses <cwd>/tmp/)
commits: |
  19612b33 — fix(scancode): replace stripped assert with ValueError in pipeline (CRIT-04)
  ff9c7983 — fix(scancode): validate --output stays within cwd (SAFE-05)
environment: |
  gmx IS available: /data/nglokwan/ompi_plumed-gmx/plumed-gromacs2023.5-gpu/bin/gmx
  (GROMACS 2023.5-plumed_2.9.3). Python 3.14.3. .gitignore:211 already has `tmp/`.
  gmx grompp dry-run not required for these robustness fixes (no topology change).
