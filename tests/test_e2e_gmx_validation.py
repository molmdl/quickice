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
    workspace = base / request.node.name.replace("::", "_")
    workspace.mkdir(parents=True, exist_ok=True)
    yield workspace


# ══════════════════════════════════════════════════════════════════════════════
# Ice Candidate (inline [moleculetype], no ITPs needed)
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# Interface (requires tip4p-ice.itp)
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# F5: Interface→Ion (minimal chain, 2 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# F6: Interface→Solute(CH4)→Ion (3 ITPs, Bug 1 fix)
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# F7: Interface→Solute(THF)→Ion (3 ITPs, Bug 1 fix)
# ══════════════════════════════════════════════════════════════════════════════


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
