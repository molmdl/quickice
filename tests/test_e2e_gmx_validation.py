"""End-to-end GROMACS grompp validation tests.

Validates that exported .gro+.top+.itp files are GROMACS-simulation-ready
by running `gmx grompp` with tests/em.mdp (energy minimization).

Tests cover:
  - Ice candidate (inline moleculetype, no ITPs needed)
  - Interface slab (#include tip4p-ice.itp)
  - F5-F7 simple chains (2-3 ITPs)
  - F1, F3, F4 complex chains (4-5 ITPs)
  - F2 (Interface→Custom→Ion, 3 ITPs, no solute)
  - F1+THF, F3+THF, F4+CH4 cross-combinations (dedup validation)

Uses conftest.py fixtures for real GenIce2-generated structures.
"""

import sys
import shutil
import pytest
from pathlib import Path

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif

from quickice.output.gromacs_writer import (
    write_gro_file,
    write_top_file,
    write_interface_gro_file,
    write_interface_top_file,
    write_ion_gro_file,
    write_ion_top_file,
    write_custom_molecule_gro_file,
    write_custom_molecule_top_file,
    write_solute_gro_file,
    write_solute_top_file,
)
from quickice.structure_generation.gromacs_ion_export import write_ion_itp
from quickice.phase_mapping.lookup import lookup_phase
from quickice.structure_generation.generator import IceStructureGenerator
from quickice.structure_generation.types import InterfaceConfig

from e2e_export_helpers import (
    parse_top_includes,
    parse_top_molecules,
    parse_gro_residue_names,
    _insert_custom_molecules,
    _insert_solutes,
    _insert_ions,
    _insert_ions_from_solute,
    _make_slab_interface,
    _hydrate_sI_ch4_candidate,
    _hydrate_sI_thf_candidate,
    _hydrate_sII_ch4_candidate,
    _hydrate_sII_thf_candidate,
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


@gmx_skipif
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

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for ice, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for ice, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for ice, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for ice, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# Interface (requires tip4p-ice.itp)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
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

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for interface, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for interface, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for interface, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for interface, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F5: Interface→Ion (minimal chain, 2 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
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

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F5, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F5, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F5, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F5, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F6: Interface→Solute(CH4)→Ion (3 ITPs, Bug 1 fix)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
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

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F6, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F6, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F6, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F6, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F7: Interface→Solute(THF)→Ion (3 ITPs, Bug 1 fix)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
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

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F7, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F7, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F7, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F7, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F1: Interface→Custom→Solute→Ion (4 ITPs, Bug 2+3)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF1GmxValidation:
    """Validate F1 chain (Interface→Custom→Solute→Ion) export passes gmx grompp.

    4 ITPs: tip4p-ice.itp, etoh.itp, ch4_liquid.itp, ion.itp
    Tests Bug 2 fix: [molecules] must use ITP moleculetype name "etoh" (not "MOL").
    Tests Bug 3 fix: No duplicate atomtypes (hc shared between GAFF2 and custom).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        # Note: SoluteInserter creates its own internal MoleculetypeRegistry and
        # auto-registers the liquid solute. No external registry needed.
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

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F1, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F1, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "MOL", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F1, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F1, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F3: Hydrate→Interface→Solute→Ion (4 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF3GmxValidation:
    """Validate F3 chain (Hydrate→Interface→Solute→Ion) export passes gmx grompp.

    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp
    Tests hydrate guest (CH4_H) + solute (CH4_L) coexistence.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        # Note: SoluteInserter creates its own internal MoleculetypeRegistry and
        # auto-registers the liquid solute. No external registry needed.
        hydrate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
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

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_H*", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F3, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F3, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_H", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F3, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F3, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F4: Hydrate→Interface→Custom→Solute→Ion (5 ITPs, ALL 3 bugs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
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
        # Note: SoluteInserter creates its own internal MoleculetypeRegistry and
        # auto-registers the liquid solute. No external registry needed.
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

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "THF_H*", "etoh", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F4, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F4, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "THF_H", "MOL", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F4, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F4, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F2: Interface→Custom→Ion (3 ITPs, Bug 2+3 without solute atomtypes)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF2GmxValidation:
    """Validate F2 chain (Interface→Custom→Ion) export passes gmx grompp.

    3 ITPs: tip4p-ice.itp, etoh.itp, ion.itp
    Tests Bug 2 fix: [molecules] uses "etoh" not "MOL" without solute atomtypes present.
    Tests Bug 3 fix: Custom-only atomtype dedup (no GAFF2 interference).
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        self.ion = _insert_ions(custom, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f2.gro")
        top_path = str(gmx_workspace / "f2.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f2.gro", top_file="f2.top")
        assert exit_code == 0, f"gmx grompp failed for F2:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "etoh", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F2, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F2, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "MOL", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F2, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F2, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F1+THF: Interface→Custom→Solute(THF)→Ion (4 ITPs, Bug 3 dedup hc)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF1ThfGmxValidation:
    """Validate F1+THF chain (Interface→Custom→Solute(THF)→Ion) export passes gmx grompp.

    4 ITPs: tip4p-ice.itp, etoh.itp, thf_liquid.itp, ion.itp
    Tests Bug 3 fix: THF solute atomtypes (os, c5, hc, h1) + etoh custom atomtypes
    (oh, ho, hc) — "hc" shared between THF GAFF2 and etoh, tests dedup.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self, interface_slab):
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f1_thf.gro")
        top_path = str(gmx_workspace / "f1_thf.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f1_thf.gro", top_file="f1_thf.top")
        assert exit_code == 0, f"gmx grompp failed for F1+THF:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "etoh", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F1+THF, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F1+THF, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "MOL", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F1+THF, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F1+THF, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F3+THF: Hydrate sI-CH4→Interface→Solute(THF)→Ion (4 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF3ThfGmxValidation:
    """Validate F3+THF chain (Hydrate sI-CH4→Interface→Solute(THF)→Ion) export passes gmx grompp.

    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, thf_liquid.itp, ion.itp
    Tests CH4_H hydrate guest (c3, hc GAFF2 atomtypes) + THF_L solute
    (os, c5, hc, h1 GAFF2 atomtypes) — "hc" shared, tests dedup.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sI_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        solute = _insert_solutes(interface, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f3_thf.gro")
        top_path = str(gmx_workspace / "f3_thf.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f3_thf.gro", top_file="f3_thf.top")
        assert exit_code == 0, f"gmx grompp failed for F3+THF:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_H*", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F3+THF, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F3+THF, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_H", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F3+THF, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F3+THF, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F4+CH4: Hydrate sI-THF→Custom→Solute(CH4)→Ion (5 ITPs, 3-source dedup)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF4Ch4GmxValidation:
    """Validate F4+CH4 chain (Hydrate sI-THF→Custom→Solute(CH4)→Ion) export passes gmx grompp.

    5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, ch4_liquid.itp, ion.itp
    Most complex dedup scenario — THREE atomtype sources with "hc" shared across
    all three:
    - THF_H hydrate guest (os, c5, hc, h1)
    - CH4_L solute (c3, hc)
    - etoh custom (oh, ho, hc)
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sI_thf_candidate()
        interface = _make_slab_interface(hydrate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f4_ch4.gro")
        top_path = str(gmx_workspace / "f4_ch4.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f4_ch4.gro", top_file="f4_ch4.top")
        assert exit_code == 0, f"gmx grompp failed for F4+CH4:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "THF_H*", "etoh", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F4+CH4, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F4+CH4, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "THF_H", "MOL", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F4+CH4, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F4+CH4, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F3-sII: Hydrate sII-CH4→Interface→Solute(CH4)→Ion (4 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF3SIIGmxValidation:
    """Validate F3-sII chain (Hydrate sII-CH4→Interface→Solute→Ion) passes gmx grompp.

    4 ITPs: tip4p-ice.itp, ch4_hydrate.itp, ch4_liquid.itp, ion.itp
    Tests sII hydrate guest export + grompp validation.
    sII has different cage structure (5^12 6^4 large + 5^12 small) from sI.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sII_ch4_candidate()
        interface = _make_slab_interface(hydrate)
        solute = _insert_solutes(interface, solute_type='CH4', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f3_sII.gro")
        top_path = str(gmx_workspace / "f3_sII.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f3_sII.gro", top_file="f3_sII.top")
        assert exit_code == 0, f"gmx grompp failed for F3-sII:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "CH4_H*", "CH4_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F3-sII, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F3-sII, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "CH4_H", "CH4_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F3-sII, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F3-sII, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# F4-sII: Hydrate sII-THF→Interface→Custom→Solute(THF)→Ion (5 ITPs)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestChainF4SIIGmxValidation:
    """Validate F4-sII chain (Hydrate sII-THF→Interface→Custom→Solute→Ion) passes gmx grompp.

    5 ITPs: tip4p-ice.itp, thf_hydrate.itp, etoh.itp, thf_liquid.itp, ion.itp
    Tests sII hydrate with full custom+solute+ion chain.
    Most complex sII chain — tests all 3 bug fixes with sII lattice.
    """

    @pytest.fixture(autouse=True)
    def _build_chain(self):
        hydrate = _hydrate_sII_thf_candidate()
        interface = _make_slab_interface(hydrate)
        custom = _insert_custom_molecules(interface, n_molecules=3)
        solute = _insert_solutes(custom, solute_type='THF', concentration=0.3)
        self.ion = _insert_ions_from_solute(solute, concentration=0.15)

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "f4_sII.gro")
        top_path = str(gmx_workspace / "f4_sII.top")
        write_ion_gro_file(self.ion, gro_path)
        write_ion_top_file(self.ion, top_path)
        write_ion_itp(gmx_workspace / "ion.itp", self.ion.na_count, self.ion.cl_count)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(gmx_workspace, gro_file="f4_sII.gro", top_file="f4_sII.top")
        assert exit_code == 0, f"gmx grompp failed for F4-sII:\n{stderr[-500:]}"

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top_keys = {"SOL", "THF_H*", "etoh", "THF_L", "NA", "CL"}
        for key in expected_top_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] for F4-sII, "
                    f"got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] for F4-sII, "
                    f"got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro_keys = {"SOL", "THF_H", "MOL", "THF_L", "NA", "CL"}
        for key in expected_gro_keys:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro for F4-sII, "
                    f"got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro for F4-sII, "
                    f"got: {sorted(unique_residues)}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# Hydrate-only (no interface step)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestHydrateGmxValidation:
    """Validate hydrate-only export passes gmx grompp.

    Tests the hydrate-only export path used by CLI --hydrate without --interface.
    Wraps HydrateStructure as InterfaceStructure (matching CLI pipeline.py behavior:
    ice_atom_count=0, water_atom_count=water_count*4).
    """

    @pytest.fixture(autouse=True)
    def _build_hydrate(self, hydrate_sI_ch4_structure):
        """Generate sI CH4 hydrate structure."""
        self.hydrate = hydrate_sI_ch4_structure
        # Wrap as InterfaceStructure (same as CLI pipeline.py:690-716)
        from quickice.structure_generation.types import (
            InterfaceStructure,
            WATER_ATOMS_PER_MOLECULE,
        )
        h = self.hydrate
        water_atom_count = h.water_count * WATER_ATOMS_PER_MOLECULE
        guest_atom_count = len(h.positions) - water_atom_count
        self.iface = InterfaceStructure(
            positions=h.positions,
            atom_names=h.atom_names,
            cell=h.cell,
            molecule_index=h.molecule_index,
            ice_atom_count=0,  # No crystalline ice in hydrate
            water_atom_count=water_atom_count,  # Hydrate water = "water" region
            ice_nmolecules=0,
            water_nmolecules=h.water_count,
            mode="hydrate",
            report=h.report,
            guest_atom_count=guest_atom_count,
            guest_nmolecules=h.guest_count,
        )

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        """Export hydrate GRO/TOP, stage ITPs, run gmx grompp."""
        gro_path = str(gmx_workspace / "hydrate.gro")
        top_path = str(gmx_workspace / "hydrate.top")
        write_interface_gro_file(self.iface, gro_path)
        write_interface_top_file(self.iface, top_path)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="hydrate.gro", top_file="hydrate.top"
        )
        assert exit_code == 0, f"gmx grompp failed for hydrate-only:\n{stderr[-500:]}"
        # Validate molecule type presence
        molecules = parse_top_molecules(top_path)
        assert "SOL" in molecules
        residue_names = parse_gro_residue_names(gro_path)
        assert "SOL" in set(residue_names)


# ══════════════════════════════════════════════════════════════════════════════
# Custom molecule-only (Interface→Custom, no Solute/Ion steps)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestCustomMoleculeGmxValidation:
    """Validate custom molecule-only export passes gmx grompp.

    Tests Interface→Custom export (no Solute/Ion steps).
    """

    @pytest.fixture(autouse=True)
    def _build_custom(self, interface_slab):
        custom = _insert_custom_molecules(interface_slab, n_molecules=3)
        self.custom = custom

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "custom.gro")
        top_path = str(gmx_workspace / "custom.top")
        write_custom_molecule_gro_file(self.custom, gro_path)
        write_custom_molecule_top_file(self.custom, top_path)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="custom.gro", top_file="custom.top"
        )
        assert exit_code == 0, f"gmx grompp failed for custom-only:\n{stderr[-500:]}"
        molecules = parse_top_molecules(top_path)
        assert "SOL" in molecules


# ══════════════════════════════════════════════════════════════════════════════
# Solute-only (Interface→Solute, no Ion step)
# ══════════════════════════════════════════════════════════════════════════════


@gmx_skipif
class TestSoluteGmxValidation:
    """Validate solute-only export passes gmx grompp.

    Tests Interface→Solute export (no Ion step).
    Uses CH4 solute (5 atoms, simpler than THF).
    """

    @pytest.fixture(autouse=True)
    def _build_solute(self, interface_slab):
        solute = _insert_solutes(interface_slab, solute_type='CH4', concentration=0.3)
        self.solute = solute

    def test_gmx_grompp_succeeds(self, gmx_workspace):
        gro_path = str(gmx_workspace / "solute.gro")
        top_path = str(gmx_workspace / "solute.top")
        write_solute_gro_file(self.solute, gro_path)
        write_solute_top_file(self.solute, top_path)
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")
        _stage_itp_files(top_path, gmx_workspace)
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace, gro_file="solute.gro", top_file="solute.top"
        )
        assert exit_code == 0, f"gmx grompp failed for solute-only:\n{stderr[-500:]}"
        molecules = parse_top_molecules(top_path)
        assert "SOL" in molecules
