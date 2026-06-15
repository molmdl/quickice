# Grompp Validation Test Coverage Analysis

**Analysis Date:** 2026-06-15

## Executive Summary

**All grompp validation tests live in a single file:** `tests/test_e2e_gmx_validation.py` (985 lines, 14 test classes). These tests exercise the **API-level export writers** directly (not GUI, not CLI subprocess). There are **zero** grompp tests for the CLI pipeline or the GUI export paths.

The CLI pipeline tests (`tests/test_cli_pipeline.py`) verify file existence and content structure but **never run `gmx grompp`**. The GUI export tests (`tests/test_output/test_gromacs_export_*.py`) mock QFileDialogs and check file creation but also **never run `gmx grompp`**.

---

## 1. Grompp Test Infrastructure

### Core Helper: `tests/e2e_export_helpers.py`

- **`run_gmx_grompp()`** (line 443): Runs `gmx grompp` as a subprocess, returns `(exit_code, stderr)`.
  - Invokes: `["gmx", "grompp", "-f", mdp_file, "-c", gro_file, "-p", top_file, "-o", tpr_file, "-maxwarn", str(maxwarn)]`
  - Timeout: 60 seconds
  - Cleans stale `.tpr` backups before running
  - **File:** `tests/e2e_export_helpers.py` lines 443–487

- **`MDP_PATH`** (line 387): Points to `tests/em.mdp` — a minimal energy minimization MDP file.
  - **File:** `tests/em.mdp` (18 lines: `integrator=steep, nsteps=500, pbc=xyz, PME, 1.0nm cutoffs`)

- **`_stage_itp_files()`** (line 391): Copies `#include`-referenced ITP files from `quickice/data/` (and `quickice/data/custom/`) to the workspace, commenting out `[atomtypes]` sections (to avoid conflicts with TOP-level `[atomtypes]`).
  - **File:** `tests/e2e_export_helpers.py` lines 391–440

### Workspace Fixture: `gmx_workspace`

- **File:** `tests/test_e2e_gmx_validation.py` lines 57–67
- Creates persistent workspace under `tmp/e2e-gmx-validation/` (named per test)
- Files persist after test run for debugging
- Does NOT clean up after the test

### Skip Conditions for GROMACS Availability

- **None found.** There are **no** `pytest.mark.skipif` markers for `gmx` availability anywhere in the test suite.
- The only skip markers found are for `pytest-qt` (in `tests/test_solute_insertion.py` lines 235, 249).
- **Risk:** If `gmx` is not on PATH, all 14 grompp tests will fail with `FileNotFoundError` or `subprocess.CalledProcessError` rather than being gracefully skipped.

---

## 2. GUI Grompp Test Coverage — By Export Path

### The 6 GUI Export Paths

| # | Export Path | GUI Exporter Class | Grompp Test? | Test Class |
|---|-------------|--------------------|--------------|------------|
| 1 | Ice | `IceGROMACSExporter` | **YES** | `TestIceCandidateGmxValidation` |
| 2 | Hydrate | `HydrateGROMACSExporter` | **NO** | — |
| 3 | Interface | `InterfaceGROMACSExporter` | **YES** | `TestInterfaceGmxValidation` |
| 4 | Custom Molecule | `CustomMoleculeGROMACSExporter` | **NO** (standalone) | — |
| 5 | Solute | `SoluteGROMACSExporter` | **NO** (standalone) | — |
| 6 | Ion | `IonGROMACSExporter` | **NO** (standalone) | — |

**Key detail:** The grompp tests in `tests/test_e2e_gmx_validation.py` call the **API-level writer functions** (`write_gro_file`, `write_ion_gro_file`, etc.) directly — they do NOT go through the GUI exporter classes. The GUI export tests in `tests/test_output/` use mocked QFileDialogs but never run `gmx grompp`.

### Detailed Coverage per GUI Export Path

**1. Ice — HAS grompp test**
- Test class: `TestIceCandidateGmxValidation` (line 75)
- File: `tests/test_e2e_gmx_validation.py` lines 75–141
- Uses: `write_gro_file()` + `write_top_file()` (inline `[moleculetype]`, no ITPs)
- Generates: 256 molecules for >2.0 nm box
- Validates: `gmx grompp` exit code 0, `[molecules]` has SOL, GRO has SOL residues

**2. Hydrate — MISSING grompp test**
- No `TestHydrateGmxValidation` class exists
- Hydrate appears only as a **starting point** in chain tests (F3, F4, F3-sII, F4-sII) where the output goes through Interface→Solute→Ion steps before grompp validation
- The **standalone hydrate-only export** (hydrate.gro + hydrate.top + tip4p-ice.itp + {guest}_hydrate.itp) has NO grompp validation
- GUI test in `tests/test_output/test_gromacs_export_hydrate.py` only checks file existence, not grompp
- **Gap:** If hydrate-only export has atom type or topology errors, they would not be caught by grompp testing

**3. Interface — HAS grompp test**
- Test class: `TestInterfaceGmxValidation` (line 148)
- File: `tests/test_e2e_gmx_validation.py` lines 148–208
- Uses: `write_interface_gro_file()` + `write_interface_top_file()` + `_stage_itp_files()`
- Requires: `tip4p-ice.itp` in workspace
- Validates: `gmx grompp` exit code 0, `[molecules]` has SOL, GRO has SOL residues

**4. Custom Molecule — NO standalone grompp test**
- No `TestCustomMoleculeGmxValidation` class exists
- Custom molecules appear in chain tests (F1, F2, F4, F1+THF, F4+CH4, F4-sII) but always as part of an Ion-level export
- The **standalone custom-only export** (custom.gro + custom.top + tip4p-ice.itp + etoh.itp) has NO grompp validation
- GUI test in `tests/test_output/test_gromacs_export_custom.py` only checks file existence
- **Note:** The chain grompp tests DO validate custom molecule ITP integration indirectly (F1, F2, F4)

**5. Solute — NO standalone grompp test**
- No `TestSoluteGmxValidation` class exists
- Solute appears in chain tests (F6, F7, F3, F1, F3+THF) but always as part of Ion-level export
- The **standalone solute-only export** (solute.gro + solute.top + tip4p-ice.itp + {solute}_liquid.itp) has NO grompp validation
- GUI test in `tests/test_output/test_gromacs_export_solute.py` only checks file existence
- **Note:** F6 and F7 chain grompp tests validate solute ITP integration (CH4_L and THF_L)

**6. Ion — NO standalone grompp test (but covered via chains)**
- No `TestIonGmxValidation` class for standalone interface→ion path
- All Ion-level grompp tests are through chain tests (F5, F6, F7, F1, F2, F3, F4)
- GUI test in `tests/test_output/test_gromacs_export_ion.py` only checks file existence

---

## 3. Chain Grompp Test Coverage

### F1–F7 Chain Definitions

| Chain | Pipeline | ITPs | Grompp Test Class | File Lines |
|-------|----------|------|-------------------|------------|
| F1 | Interface→Custom→Solute→Ion | 4 | `TestChainF1GmxValidation` | 399–458 |
| F2 | Interface→Custom→Ion | 3 | `TestChainF2GmxValidation` | 601–657 |
| F3 | Hydrate sI-CH4→Interface→Solute→Ion | 4 | `TestChainF3GmxValidation` | 465–524 |
| F4 | Hydrate sI-THF→Interface→Custom→Solute→Ion | 5 | `TestChainF4GmxValidation` | 531–594 |
| F5 | Interface→Ion | 2 | `TestChainF5GmxValidation` | 215–268 |
| F6 | Interface→Solute(CH4)→Ion | 3 | `TestChainF6GmxValidation` | 275–330 |
| F7 | Interface→Solute(THF)→Ion | 3 | `TestChainF7GmxValidation` | 337–392 |

### Extended Chain Grompp Tests

| Chain | Pipeline | ITPs | Grompp Test Class | File Lines |
|-------|----------|------|-------------------|------------|
| F1+THF | Interface→Custom→Solute(THF)→Ion | 4 | `TestChainF1ThfGmxValidation` | 664–721 |
| F3+THF | Hydrate sI-CH4→Interface→Solute(THF)→Ion | 4 | `TestChainF3ThfGmxValidation` | 728–786 |
| F4+CH4 | Hydrate sI-THF→Custom→Solute(CH4)→Ion | 5 | `TestChainF4Ch4GmxValidation` | 793–855 |
| F3-sII | Hydrate sII-CH4→Interface→Solute→Ion | 4 | `TestChainF3SIIGmxValidation` | 862–920 |
| F4-sII | Hydrate sII-THF→Interface→Custom→Solute→Ion | 5 | `TestChainF4SIIGmxValidation` | 927–985 |

### What Each Chain Grompp Test Validates

All 12 chain grompp tests follow the same pattern:
1. Build chain using `e2e_export_helpers.py` helper functions
2. Write `.gro` and `.top` files to `gmx_workspace`
3. Generate `ion.itp` via `write_ion_itp()`
4. Copy `em.mdp` from `tests/em.mdp`
5. Stage ITP files via `_stage_itp_files()` (copies from `quickice/data/`)
6. Run `gmx grompp` via `run_gmx_grompp()`
7. Assert exit code == 0
8. Validate `[molecules]` section has expected molecule types
9. Validate GRO residue names match expected set

### Bug-Specific Coverage in Chain Tests

| Bug | Fix Validated By | What It Tests |
|-----|-----------------|---------------|
| Bug 1: Solute atomtypes missing | F6, F7, F1+THF, F3+THF | CH4/THF solute atomtypes (c3, hc, os, c5, h1) in TOP `[atomtypes]` |
| Bug 2: `[molecules]` uses "MOL" instead of ITP name | F1, F2, F4, F4-sII | Custom moleculetype name "etoh" in `[molecules]` (not "MOL") |
| Bug 3: Duplicate atomtypes | F1, F2, F4, F1+THF, F4+CH4, F4-sII | "hc" shared across GAFF2 solute + custom molecule atomtypes |
| 3-source dedup | F4+CH4 | "hc" shared across THF_H + CH4_L + etoh (THREE sources) |

---

## 4. CLI Grompp Test Coverage

### CLI Pipeline: `quickice/cli/pipeline.py`

The CLI pipeline (`CLIPipeline.execute()`) supports all 6 export paths:
- **Ice:** `write_gro_file()` + `write_top_file()` (line 685–687)
- **Hydrate:** Wraps HydrateStructure as InterfaceStructure, then `write_interface_gro_file()` + `write_interface_top_file()` (lines 688–716)
- **Interface:** `write_interface_gro_file()` + `write_interface_top_file()` (lines 717–719)
- **Custom:** `write_custom_molecule_gro_file()` + `write_custom_molecule_top_file()` (lines 720–722)
- **Solute:** `write_solute_gro_file()` + `write_solute_top_file()` (lines 723–725)
- **Ion:** `write_ion_gro_file()` + `write_ion_top_file()` (lines 726–728)

Plus ITP file copying via `copy_itp_files_for_structure()` from `quickice/cli/itp_helpers.py`.

### CLI Test Files and Their Coverage

**`tests/test_cli_pipeline.py`** (679 lines):
- `TestPipelineFlagValidation` (8 tests): Flag validation, exit code 2
- `TestPipelineExitCodes` (3 tests): Exit codes 0, 1, 2
- `TestPipelineProgressReporting` (2 tests): `[PROGRESS]` on stderr
- `TestPipelineBasicWorkflows` (6 tests): File existence checks only
- `TestPipelineAdvancedWorkflows` (6 tests): File existence checks only
- `TestPipelineExportCorrectness` (4 tests): GRO atom count, TOP molecules section, ITP existence, `--no-overwrite`

**`tests/test_cli_integration.py`** (288 lines):
- Input validation only (temperature, pressure, nmolecules bounds)
- No export validation at all

**Result: CLI tests have ZERO grompp validation.** All CLI workflow tests verify that:
1. The subprocess exits with code 0
2. Expected output files exist (`.gro`, `.top`, `.itp`)
3. GRO/TOP content is structurally valid (atom count, `[molecules]` section, ITP count)

None of them run `gmx grompp` on the exported files. If the CLI export produces files that are structurally plausible but fail GROMACS preprocessing, the CLI tests would pass while the actual simulation would fail.

---

## 5. Cross-Reference: GUI vs CLI vs API Grompp Coverage

| Export Path | API Grompp | GUI Grompp | CLI Grompp |
|-------------|-----------|-----------|-----------|
| Ice (standalone) | YES (`TestIceCandidateGmxValidation`) | NO | NO |
| Hydrate (standalone) | NO | NO | NO |
| Interface (standalone) | YES (`TestInterfaceGmxValidation`) | NO | NO |
| Custom (standalone) | NO | NO | NO |
| Solute (standalone) | NO | NO | NO |
| Ion (standalone) | NO | NO | NO |
| F1 (Iface→Custom→Solute→Ion) | YES | NO | NO |
| F2 (Iface→Custom→Ion) | YES | NO | NO |
| F3 (Hydrate→Iface→Solute→Ion) | YES | NO | NO |
| F4 (Hydrate→Iface→Custom→Solute→Ion) | YES | NO | NO |
| F5 (Iface→Ion) | YES | NO | NO |
| F6 (Iface→Solute(CH4)→Ion) | YES | NO | NO |
| F7 (Iface→Solute(THF)→Ion) | YES | NO | NO |
| F1+THF | YES | NO | NO |
| F3+THF | YES | NO | NO |
| F4+CH4 | YES | NO | NO |
| F3-sII | YES | NO | NO |
| F4-sII | YES | NO | NO |

**Summary:** Only the API-level export path has grompp validation. GUI and CLI paths have zero grompp coverage.

---

## 6. Specific Coverage Gaps

### Gap 1: Hydrate-only export has NO grompp validation

- **What's missing:** A `TestHydrateGmxValidation` class that exports a HydrateStructure directly (as the CLI does by wrapping it as InterfaceStructure) and runs `gmx grompp`
- **Impact:** Hydrate-only CLI output (`--hydrate --lattice-type sI --guest CH4` without `--interface`) uses a unique code path (HydrateStructure→InterfaceStructure wrapper, lines 688–716 in `quickice/cli/pipeline.py`) that differs from all chain tests. If this wrapper produces invalid topology, it would not be caught.
- **Files:** `quickice/cli/pipeline.py` lines 688–716, `tests/test_e2e_gmx_validation.py` (missing class)

### Gap 2: Solute-only export has NO grompp validation

- **What's missing:** A grompp test for `write_solute_gro_file()` + `write_solute_top_file()` output
- **Impact:** Solute-only export (Interface→Solute, no Ion step) uses a different TOP file format than Ion-level export. Solute-only TOP includes solute atomtypes but not ion atomtypes. This code path is untested by grompp.
- **Files:** `quickice/output/gromacs_writer.py` (`write_solute_top_file`), `tests/test_output/test_gromacs_export_solute.py`

### Gap 3: Custom-only export has NO grompp validation

- **What's missing:** A grompp test for `write_custom_molecule_gro_file()` + `write_custom_molecule_top_file()` output
- **Impact:** Custom-only export (Interface→Custom, no Solute/Ion steps) is a valid user path. This TOP file has custom molecule atomtypes but no solute or ion atomtypes.
- **Files:** `quickice/output/gromacs_writer.py` (`write_custom_molecule_top_file`), `tests/test_output/test_gromacs_export_custom.py`

### Gap 4: CLI pipeline has ZERO grompp validation

- **What's missing:** No CLI test runs `gmx grompp` on subprocess output
- **Impact:** The CLI pipeline uses a **different ITP staging mechanism** (`quickice/cli/itp_helpers.py` `copy_itp_files_for_structure()`) than the API grompp tests (`_stage_itp_files()` from `e2e_export_helpers.py`). If the CLI ITP staging has bugs (missing ITPs, wrong paths), the grompp tests would not catch them.
- **Files:** `tests/test_cli_pipeline.py`, `quickice/cli/itp_helpers.py`

### Gap 5: No GROMACS skip marker

- **What's missing:** No `pytest.mark.skipif` for when `gmx` is not installed
- **Impact:** If GROMACS is not on PATH, all 14 grompp tests fail with a subprocess error instead of being skipped gracefully. This causes CI failures in environments without GROMACS.
- **Files:** `tests/test_e2e_gmx_validation.py`, `tests/conftest.py`

### Gap 6: Ice-only grompp test uses only Ice Ih

- **What's missing:** Grompp tests for Ice Ic, Ice III, Ice V, Ice VI, Ice VII, Ice VIII exports
- **Impact:** Ice Ic uses a different lattice (diamond vs hexagonal) that might produce different GRO formatting issues. High-pressure phases (III–VIII) use different cell types.
- **Files:** `tests/test_e2e_gmx_validation.py` (only `TestIceCandidateGmxValidation` at 250K/0.1MPa = Ice Ih)

---

## 7. How the Grompp Tests Are Structured

### Pattern (from `tests/test_e2e_gmx_validation.py`):

```python
class TestChainF1GmxValidation:
    """Docstring with chain description, ITP count, bugs tested."""

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        """Build chain using e2e_export_helpers functions."""
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        """Export files, stage ITPs, run gmx grompp, assert exit code 0."""
        # 1. Write GRO/TOP
        gro_path = str(gmx_workspace / "f1.gro")
        top_path = str(gmx_workspace / "f1.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)

        # 2. Generate ion.itp
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)

        # 3. Copy MDP file
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")

        # 4. Stage ITP files (copies from quickice/data/ with atomtypes commented out)
        _stage_itp_files(top_path, gmx_workspace)

        # 5. Run gmx grompp
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="f1.gro", top_file="f1.top"
        )
        assert exit_code == 0, f"gmx grompp failed for F1:\n{stderr[-500:]}"

        # 6. Validate TOP [molecules] contents
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            assert key in molecules, ...

        # 7. Validate GRO residue names
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "MOL", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            assert key in unique_residues, ...
```

### ITP Staging Details

The `_stage_itp_files()` function (from `tests/e2e_export_helpers.py`):
1. Parses `#include` directives from the TOP file
2. Locates ITP files in `quickice/data/` or `quickice/data/custom/`
3. Comments out `[atomtypes]` sections in ITPs (to avoid conflicts with TOP-level `[atomtypes]`)
4. Skips `ion.itp` (generated in workspace by `write_ion_itp()`)
5. Writes ITPs to the workspace directory

**This differs from CLI staging** which uses `quickice/cli/itp_helpers.py` `copy_itp_files_for_structure()` — a different code path.

---

## 8. Recommendations

1. **Add `TestHydrateGmxValidation`** — Test hydrate-only export (wrapping as InterfaceStructure per CLI pattern) with grompp. Covers the unique CLI hydrate→interface wrapper path.

2. **Add CLI grompp tests** — After CLI pipeline subprocess completes, run `gmx grompp` on the output directory. This validates the CLI-specific ITP staging path (`quickice/cli/itp_helpers.py`).

3. **Add `pytest.mark.skipif` for GROMACS availability** — Check `shutil.which("gmx")` and skip grompp tests if not found. Add to `tests/conftest.py`.

4. **Add standalone Solute and Custom grompp tests** — Validate intermediate export levels that users can reach from the GUI.

5. **Add pocket and piece mode grompp tests** — Current Interface grompp test only uses slab mode. Pocket and piece modes may produce different box geometries that affect grompp.

---

*Analysis by codebase mapper — 2026-06-15*
