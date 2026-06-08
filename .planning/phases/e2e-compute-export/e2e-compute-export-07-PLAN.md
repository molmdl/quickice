---
phase: e2e-compute-export
plan: 07
type: execute
wave: 2
depends_on: ["e2e-compute-export-06"]
files_modified:
  - tests/test_e2e_gmx_validation.py
autonomous: true

must_haves:
  truths:
    - "Ice candidate exported files (256 molecules) pass gmx grompp without errors"
    - "Interface exported files pass gmx grompp without errors"
    - "F5 chain (Interface→Ion) exported files pass gmx grompp without errors"
    - "F6 chain (Interface→Solute(CH4)→Ion) exported files pass gmx grompp without errors"
    - "F7 chain (Interface→Solute(THF)→Ion) exported files pass gmx grompp without errors"
    - "F1 chain (Interface→Custom→Solute→Ion) exported files pass gmx grompp without errors"
    - "F3 chain (Hydrate→Interface→Solute→Ion) exported files pass gmx grompp without errors"
    - "F4 chain (Hydrate→Interface→Custom→Solute→Ion) exported files pass gmx grompp without errors"
  artifacts:
    - path: "tests/test_e2e_gmx_validation.py"
      provides: "GROMACS grompp validation tests for all export scenarios"
      min_lines: 200
  key_links:
    - from: "tests/test_e2e_gmx_validation.py"
      to: "tests/e2e_export_helpers.py"
      via: "import _stage_itp_files, run_gmx_grompp, MDP_PATH and chain-building helpers"
      pattern: "from e2e_export_helpers import"
    - from: "tests/test_e2e_gmx_validation.py"
      to: "quickice/output/gromacs_writer.py"
      via: "import write_*_gro_file and write_*_top_file for each structure type"
      pattern: "from quickice.output.gromacs_writer import"
---

<objective>
Create GROMACS grompp validation tests for all export scenarios.

Purpose: Validate that exported files are not just format-correct but GROMACS-simulation-ready.
These tests exercise the full pipeline: real structure generation → writer function → gmx grompp.
Each test verifies that `gmx grompp` can process the exported .gro+.top+.itp+.mdp files without
fatal errors (exit code 0).

Output: test_e2e_gmx_validation.py with 8 test classes covering ice candidate, interface,
and all 7 chain scenarios (F1-F7), minus F2 which is a subset of F1.
</objective>

<execution_context>
@~/.config/opencode/get-shit-done/workflows/execute-plan.md
@~/.config/opencode/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/e2e-compute-export/e2e-compute-export-06-SUMMARY.md
@tests/e2e_export_helpers.py
@tests/conftest.py
@tests/test_e2e_chain_export_1.py
@tests/test_e2e_chain_export_2.py
@tests/em.mdp
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create test_e2e_gmx_validation.py with ice, interface, and simple chain tests</name>
  <files>tests/test_e2e_gmx_validation.py</files>
  <action>
Create `tests/test_e2e_gmx_validation.py` with GROMACS grompp validation tests.

The file structure follows existing test patterns (see test_e2e_chain_export_1.py for reference):
- `sys.path.insert(0, ...)` for e2e_export_helpers import
- Uses conftest.py fixtures (ice_ih_candidate, interface_slab, etc.)
- Each test class builds the structure, exports files, stages ITPs, runs gmx grompp, asserts exit code

**Test file skeleton:**

```python
"""End-to-end GROMACS grompp validation tests.

Validates that exported .gro+.top+.itp files are GROMACS-simulation-ready
by running `gmx grompp` with tests/em.mdp (energy minimization).

Tests cover:
  - Ice candidate (inline moleculetype, no ITPs needed)
  - Interface slab (#include tip4p-ice.itp)
  - F5-F7 simple chains (2-3 ITPs)
  - F1, F3, F4 complex chains (4-5 ITPs)

Uses conftest.py fixtures for real GenIce2-generated structures.
"""

import sys
import shutil
import pytest
from pathlib import Path

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from quickice.output.gromacs_writer import (
    write_gro_file,
    write_top_file,
    write_interface_gro_file,
    write_interface_top_file,
    write_ion_gro_file,
    write_ion_top_file,
)
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.types import InterfaceConfig

from e2e_export_helpers import (
    parse_top_includes,
    _insert_custom_molecules,
    _insert_solutes,
    _insert_ions,
    _insert_ions_from_solute,
    _make_slab_interface,
    _hydrate_sI_ch4_candidate,
    _hydrate_sI_thf_candidate,
    _stage_itp_files,
    run_gmx_grompp,
    MDP_PATH,
)


@pytest.fixture
def gmx_workspace(request):
    """Persistent workspace under tmp/e2e-gmx-validation/ for GROMACS grompp.
    
    Each test gets its own subdirectory named after the test.
    Files persist after test run for debugging.
    """
    base = Path(__file__).parent.parent / "tmp" / "e2e-gmx-validation"
    workspace = base / request.node.name
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace
```

**Test Class 1: Ice Candidate (256 molecules for larger box)**

The conftest fixture uses 96 molecules which produces a box too small for 1.0 nm cutoffs
(~1.5 x 1.5 x 1.8 nm, half shortest = 0.74 nm < 1.0 nm). Generate 256 molecules inline
(~2.2 x 2.3 x 2.7 nm, half shortest = 1.1 nm > 1.0 nm).

```python
class TestIceCandidateGmxValidation:
    """Validate ice candidate export passes gmx grompp.
    
    Uses write_gro_file/write_top_file (inline [moleculetype], no ITPs needed).
    Generates 256 molecules for a box large enough for 1.0 nm cutoffs.
    """

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        """Ice candidate .gro+.top+em.mdp passes gmx grompp."""
        # Generate larger ice candidate (256 molecules for > 2.0 nm box)
        phase_info = lookup_phase(250, 0.1)
        gen = IceStructureGenerator(phase_info, 256)
        candidates = gen.generate_all(1)
        candidate = candidates[0]

        # Export files
        gro_path = str(gmx_workspace / "ice.gro")
        top_path = str(gmx_workspace / "ice.top")
        write_gro_file(candidate, gro_path)
        write_top_file(candidate, top_path)

        # Copy MDP
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")

        # No ITP staging needed — ice candidate uses inline [moleculetype]

        # Run gmx grompp
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="ice.gro", top_file="ice.top"
        )
        assert exit_code == 0, (
            f"gmx grompp failed for ice candidate:\n{stderr[-500:]}"
        )
```

**Test Class 2: Interface**

Uses conftest.py `interface_slab` fixture (3.0 x 3.0 x 8.0 nm box, large enough).

```python
class TestInterfaceGmxValidation:
    """Validate interface export passes gmx grompp.
    
    Uses write_interface_gro_file/write_interface_top_file.
    Requires tip4p-ice.itp in same directory.
    """

    def test_gmx_grompp_succeeds(self, interface_slab, gmx_workspace):
        """Interface .gro+.top+tip4p-ice.itp+em.mdp passes gmx grompp."""
        gro_path = str(gmx_workspace / "iface.gro")
        top_path = str(gmx_workspace / "iface.top")
        write_interface_gro_file(interface_slab, gro_path)
        write_interface_top_file(interface_slab, top_path)

        # Copy MDP
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")

        # Stage ITPs
        _stage_itp_files(top_path, gmx_workspace)

        # Run gmx grompp
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="iface.gro", top_file="iface.top"
        )
        assert exit_code == 0, (
            f"gmx grompp failed for interface:\n{stderr[-500:]}"
        )
```

**Test Classes 3-5: Simple chains F5, F6, F7**

Each uses `interface_slab` fixture + chain-building helpers. Pattern:

```python
class TestChainF5GmxValidation:
    """Validate F5 chain (Interface→Ion) export passes gmx grompp.
    
    2 ITPs: tip4p-ice.itp, ion.itp
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        self.ion = _insert_ions(interface_slab, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f5.gro")
        top_path = str(gmx_workspace / "f5.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f5.gro", top_file="f5.top")
        assert exit_code == 0, f"gmx grompp failed for F5:\n{stderr[-500:]}"


class TestChainF6GmxValidation:
    """Validate F6 chain (Interface→Solute(CH4)→Ion) export passes gmx grompp.
    
    3 ITPs: tip4p-ice.itp, ch4_liquid.itp, ion.itp
    Tests Bug 1 fix: CH4 solute atomtypes (c3, hc) must be in TOP [atomtypes].
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f6.gro")
        top_path = str(gmx_workspace / "f6.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f6.gro", top_file="f6.top")
        assert exit_code == 0, f"gmx grompp failed for F6:\n{stderr[-500:]}"


class TestChainF7GmxValidation:
    """Validate F7 chain (Interface→Solute(THF)→Ion) export passes gmx grompp.
    
    3 ITPs: tip4p-ice.itp, thf_liquid.itp, ion.itp
    Tests Bug 1 fix: THF solute atomtypes (os, c5, hc, h1) must be in TOP [atomtypes].
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        solute = _insert_solutes(interface_slab, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f7.gro")
        top_path = str(gmx_workspace / "f7.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f7.gro", top_file="f7.top")
        assert exit_code == 0, f"gmx grompp failed for F7:\n{stderr[-500:]}"
```

IMPORTANT: Use the exact same chain-building pattern from existing chain tests. F6/F7 use
`_insert_ions_from_solute()` (BUG I5 workaround). F5 uses `_insert_ions()` directly (no workaround).

Each test follows the same 6-step pattern:
1. Write GRO to workspace
2. Write TOP to workspace
3. Generate ion.itp to workspace
4. Copy MDP to workspace
5. Stage ITP files using `_stage_itp_files()`
6. Run `run_gmx_grompp()` and assert exit_code == 0

For the ice candidate test ONLY: skip step 3 (no ions) and step 5 (no ITPs needed).
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_gmx_validation.py::TestIceCandidateGmxValidation -xvs 2>&1 | tail -10 && python -m pytest tests/test_e2e_gmx_validation.py::TestInterfaceGmxValidation -xvs 2>&1 | tail -5 && python -m pytest tests/test_e2e_gmx_validation.py::TestChainF5GmxValidation -xvs 2>&1 | tail -5</verify>
  <done>
1. TestIceCandidateGmxValidation::test_gmx_grompp_succeeds PASSES
2. TestInterfaceGmxValidation::test_gmx_grompp_succeeds PASSES
3. TestChainF5GmxValidation::test_gmx_grompp_succeeds PASSES
4. TestChainF6GmxValidation::test_gmx_grompp_succeeds PASSES
5. TestChainF7GmxValidation::test_gmx_grompp_succeeds PASSES
6. test_e2e_gmx_validation.py has 5 test classes, 5 test methods
  </done>
</task>

<task type="auto">
  <name>Task 2: Add F1, F3, F4 complex chain grompp validation tests</name>
  <files>tests/test_e2e_gmx_validation.py</files>
  <action>
Add 3 more test classes to the EXISTING test_e2e_gmx_validation.py (append after TestChainF7GmxValidation):

**Test Class 6: F1 (Interface→Custom→Solute→Ion)**

```python
class TestChainF1GmxValidation:
    """Validate F1 chain (Interface→Custom→Solute→Ion) export passes gmx grompp.
    
    4 ITPs: tip4p-ice.itp, etoh.itp, ch4_liquid.itp, ion.itp
    Tests Bug 2 fix: [molecules] must use ITP moleculetype name "etoh" (not "MOL").
    Tests Bug 3 fix: No duplicate atomtypes (hc shared between GAFF2 and custom).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f1.gro")
        top_path = str(gmx_workspace / "f1.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f1.gro", top_file="f1.top")
        assert exit_code == 0, f"gmx grompp failed for F1:\n{stderr[-500:]}"
```

**Test Class 7: F3 (Hydrate→Interface→Solute→Ion)**

```python
class TestChainF3GmxValidation:
    """Validate F3 chain (Hydrate→Interface→Solute→Ion) export passes gmx grompp.
    
    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp
    Tests hydrate guest (CH4_H) + solute (CH4_L) coexistence — same GAFF2 atomtypes
    used for both, must not duplicate.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
        registry = MoleculetypeRegistry()
        registry.register_liquid_solute("CH4")
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f3.gro")
        top_path = str(gmx_workspace / "f3.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f3.gro", top_file="f3.top")
        assert exit_code == 0, f"gmx grompp failed for F3:\n{stderr[-500:]}"
```

Wait — F3 starts with a HYDRATE, not the interface_slab fixture. The interface_slab
fixture uses ice_ih_candidate. For F3, we need a hydrate→interface chain.

Use `_hydrate_sI_ch4_candidate()` + `_make_slab_interface()` (both from e2e_export_helpers.py)
to generate the hydrate-based interface inline. This matches the pattern in test_e2e_chain_export_1.py.

Also need to register the hydrate guest before solute insertion (established pattern from
Plan 04 — see STATE.md decision "Register hydrate guest before insert_solutes for F3/F4").

Corrected F3 test:

```python
class TestChainF3GmxValidation:
    """Validate F3 chain (Hydrate→Interface→Solute→Ion) export passes gmx grompp.
    
    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp
    Tests hydrate guest (CH4_H) + solute (CH4_L) coexistence.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
        registry = MoleculetypeRegistry()
        registry.register_hydrate_guest("CH4")
        registry.register_liquid_solute("CH4")
        hydrate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        # ... same 6-step pattern ...
```

**Test Class 8: F4 (Hydrate→Interface→Custom→Solute→Ion)**

Most complex chain — 5 ITPs. Tests ALL three bug fixes simultaneously:
- Bug 1: THF solute atomtypes (os, c5, hc, h1) in TOP
- Bug 2: Custom molecule moleculetype name "etoh" in [molecules]
- Bug 3: Dedup hc/h1 between THF guest GAFF2 and etoh custom

```python
class TestChainF4GmxValidation:
    """Validate F4 chain (Hydrate→Interface→Custom→Solute→Ion) export passes gmx grompp.
    
    5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp, ion.itp
    Most complex chain — tests ALL three bug fixes:
    - Solute atomtypes (THF: os, c5, hc, h1) must be in TOP [atomtypes]
    - Custom moleculetype name "etoh" in [molecules] (not "MOL")
    - No duplicate atomtypes (hc, h1 shared between THF GAFF2 and etoh custom)
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry
        registry = MoleculetypeRegistry()
        registry.register_hydrate_guest("THF")
        hydrate = _hydrate_sI_thf_candidate()
        interface = _make_slab_interface(hydrate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f4.gro")
        top_path = str(gmx_workspace / "f4.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f4.gro", top_file="f4.top")
        assert exit_code == 0, f"gmx grompp failed for F4:\n{stderr[-500:]}"
```

NOTE: F3 and F4 do NOT use conftest.py interface_slab fixture — they generate their
interface from a hydrate candidate using inline helper calls. This matches the pattern
in test_e2e_chain_export_1.py where F3/F4 are also built inline.

NOTE: F1 DOES use interface_slab fixture (same as existing F1 test in
test_e2e_chain_export_1.py) because F1 starts from a regular ice-based interface.
  </action>
  <verify>cd /share/home/nglokwan/quickice && python -m pytest tests/test_e2e_gmx_validation.py -xvs 2>&1 | tail -25</verify>
  <done>
1. All 8 gmx validation tests pass (ice, interface, F5, F6, F7, F1, F3, F4)
2. Each test creates workspace under tmp/e2e-gmx-validation/ with .gro, .top, .itp, .mdp, .tpr files
3. test_e2e_gmx_validation.py has 8 test classes, 8 test methods
4. F4 (most complex chain with 5 ITPs) passes gmx grompp — all 3 bug fixes validated
5. All 116 existing bridge tests still pass
</done>
</task>

</tasks>

<verification>
1. All gmx validation tests pass: `python -m pytest tests/test_e2e_gmx_validation.py -xvs`
2. All existing bridge tests still pass: `python -m pytest tests/test_e2e_*.py -x -q`
3. Verify workspace files exist after test run: `ls tmp/e2e-gmx-validation/`
4. Verify .tpr files were generated: `ls tmp/e2e-gmx-validation/*/em.tpr`
</verification>

<success_criteria>
1. 8/8 gmx grompp validation tests pass with exit code 0
2. F6 (CH4 solute, no custom) passes — validates Bug 1 fix (solute atomtypes)
3. F1 (custom + solute + ions) passes — validates Bug 2 fix (moleculetype name)
4. F4 (THF + custom + solute + ions) passes — validates Bug 3 fix (dedup atomtypes)
5. All 116 existing bridge tests continue to pass
6. Total test count increases from 116 to 124
</success_criteria>

<output>
After completion, create `.planning/phases/e2e-compute-export/e2e-compute-export-07-SUMMARY.md`
</output>
