# Codebase Concerns

**Analysis Date:** 2026-06-15

## Tech Debt

**CLI grompp validation gap:**
- Issue: CLI pipeline tests verify file existence but never run `gmx grompp` on subprocess output
- Files: `tests/test_cli_pipeline.py`, `quickice/cli/pipeline.py`
- Impact: CLI ITP staging (`quickice/cli/itp_helpers.py`) is a different code path from API-level staging (`tests/e2e_export_helpers.py` `_stage_itp_files()`). CLI bugs that produce structurally plausible but GROMACS-invalid output would pass all CLI tests
- Fix approach: Add post-export grompp validation to CLI pipeline tests (run `gmx grompp` on the output directory after subprocess completes)

**Hydrate-only export has no grompp test:**
- Issue: No `TestHydrateGmxValidation` exists; hydrate appears only as starting point in chain tests (F3, F4, F3-sII, F4-sII) where output goes through Interface→Solute→Ion before grompp
- Files: `tests/test_e2e_gmx_validation.py`, `quickice/cli/pipeline.py` lines 688–716
- Impact: CLI hydrate-only path wraps HydrateStructure as InterfaceStructure — a unique code path untested by grompp
- Fix approach: Add `TestHydrateGmxValidation` that tests hydrate-only export with sI-CH4 and sI-THF

**Intermediate export levels lack grompp validation:**
- Issue: Solute-only and Custom-only export paths have no grompp tests
- Files: `quickice/output/gromacs_writer.py` (`write_solute_top_file`, `write_custom_molecule_top_file`)
- Impact: If these intermediate TOP files have atomtype errors, they won't be caught until a user tries to run grompp on them
- Fix approach: Add `TestSoluteGmxValidation` and `TestCustomGmxValidation` classes

## Known Bugs

**No graceful skip when GROMACS not installed:**
- Symptoms: All 14 grompp tests fail with subprocess error when `gmx` is not on PATH
- Files: `tests/test_e2e_gmx_validation.py`, `tests/conftest.py`
- Trigger: Run test suite in environment without GROMACS
- Workaround: Manually skip with `pytest -k "not gmx"` but this is undocumented

## Security Considerations

**Subprocess execution in tests:**
- Risk: `run_gmx_grompp()` runs `gmx grompp` as subprocess with `shell=False` and explicit args — no injection risk
- Files: `tests/e2e_export_helpers.py` lines 443–487
- Current mitigation: Proper subprocess usage with explicit arg list
- Recommendations: No changes needed

## Performance Bottlenecks

**Grompp tests are slow but isolated:**
- Problem: Each grompp test requires GenIce2 generation (~3-5s) + file writing + subprocess grompp (~2-5s)
- Files: `tests/test_e2e_gmx_validation.py`
- Cause: Tests use real structure generation (not mocked)
- Improvement path: Module-scoped fixtures in `conftest.py` amortize generation cost across test classes, but each test class still generates its own chain

## Fragile Areas

**ITP staging dual path:**
- Files: `tests/e2e_export_helpers.py` `_stage_itp_files()` vs `quickice/cli/itp_helpers.py` `copy_itp_files_for_structure()`
- Why fragile: Two separate ITP staging implementations; API tests use one, CLI uses the other. Divergence could introduce CLI-only bugs
- Safe modification: Ensure both paths produce identical ITP file sets; add integration test that validates CLI output matches API output
- Test coverage: API path is grompp-validated; CLI path is not

## Missing Critical Features

**No GROMACS availability detection:**
- Problem: Tests have no `pytest.mark.skipif` for when `gmx` is not installed
- Blocks: Running test suite in CI environments without GROMACS

**No grompp coverage for GUI export paths:**
- Problem: GUI export tests (`tests/test_output/`) mock QFileDialogs but never validate grompp
- Blocks: Detecting GUI export bugs that produce GROMACS-invalid files

## Test Coverage Gaps

**Hydrate-only export grompp validation:**
- What's not tested: HydrateStructure exported directly (no chain)
- Files: `quickice/cli/pipeline.py` lines 688–716, `tests/test_output/test_gromacs_export_hydrate.py`
- Risk: Hydrate-only CLI code path produces invalid .top/.gro without detection
- Priority: High

**CLI subprocess grompp validation:**
- What's not tested: Running `gmx grompp` on CLI pipeline output
- Files: `tests/test_cli_pipeline.py` (all workflow tests check file existence only)
- Risk: CLI ITP staging bugs go undetected
- Priority: High

**Solute-only grompp validation:**
- What's not tested: `write_solute_gro_file()` + `write_solute_top_file()` output validated by grompp
- Files: `quickice/output/gromacs_writer.py`, `tests/test_e2e_solute_export.py`
- Risk: Solute-only export produces invalid GROMACS topology
- Priority: Medium

**Custom-only grompp validation:**
- What's not tested: `write_custom_molecule_gro_file()` + `write_custom_molecule_top_file()` output validated by grompp
- Files: `quickice/output/gromacs_writer.py`, `tests/test_e2e_custom_export.py`
- Risk: Custom-only export produces invalid GROMACS topology
- Priority: Medium

**Ice phase variety grompp:**
- What's not tested: Ice Ic, Ice III, Ice V, Ice VI, Ice VII, Ice VIII exports
- Files: `tests/test_e2e_gmx_validation.py` (only Ice Ih tested)
- Risk: Different lattice types may produce GRO formatting issues for other phases
- Priority: Low

---

*Concerns audit: 2026-06-15*
