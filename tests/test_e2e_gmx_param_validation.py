"""Parameterized grompp validation tests for 27 untested chain combinations.

Complements test_e2e_gmx_validation.py (18 class-based tests covering deepest
chains F1-F7 + sII + hydrate/custom/solute standalone + ice/interface) with
27 parameterized test cases for all remaining untested hydrate→interface chain
combinations.

Derivation: 4 hydrate types × {custom:yes/no} × {solute:none/CH4/THF} × {ion:yes/no}
= 48 total combos minus 13 already-tested (F3, F3+THF, F4, F4+CH4, F4-sII,
F3-sII, F4-CH4-hydrate, ice, interface, hydrate-only, custom-only, solute-only,
F5/F6/F7) minus 8 non-hydrate interface-only combos (bridge tests) = 27.

Uses pytest.mark.parametrize with ChainParams NamedTuple for systematic coverage
in ~150 lines vs ~800 lines for 27 individual classes.
"""

import sys
import shutil
import pytest
from pathlib import Path
from typing import NamedTuple, Optional

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif

from quickice.output.gromacs_writer import (
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

from e2e_export_helpers import (
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
    assert_itp_completeness,
    run_gmx_grompp,
    MDP_PATH,
)


# ── Chain parameters ──────────────────────────────────────────────────────────

class ChainParams(NamedTuple):
    """Parameters defining a hydrate→interface chain combination."""
    id: str
    hydrate_type: str
    has_custom: bool
    solute_type: Optional[str]
    has_ion: bool


# ── Hydrate builders ──────────────────────────────────────────────────────────

_HYDRATE_BUILDERS = {
    "sI-CH4": _hydrate_sI_ch4_candidate,
    "sI-THF": _hydrate_sI_thf_candidate,
    "sII-CH4": _hydrate_sII_ch4_candidate,
    "sII-THF": _hydrate_sII_thf_candidate,
}


# ── Hydrate guest molecule naming ─────────────────────────────────────────────

_HYDRATE_GUEST = {
    "sI-CH4": ("CH4_H*", "CH4_H"),
    "sI-THF": ("THF_H*", "THF_H"),
    "sII-CH4": ("CH4_H*", "CH4_H"),
    "sII-THF": ("THF_H*", "THF_H"),
}


# ── 27 untested chain combinations ───────────────────────────────────────────

CHAIN_COMBINATIONS = [
    ChainParams("sI-CH4_custom_ion",      "sI-CH4",  True,  None,  True),
    ChainParams("sI-CH4_custom_thf",      "sI-CH4",  True,  "THF", False),
    ChainParams("sI-CH4_custom_thf_ion",  "sI-CH4",  True,  "THF", True),
    ChainParams("sI-CH4_ion",             "sI-CH4",  False, None,  True),
    ChainParams("sI-THF_custom_ion",     "sI-THF",  True,  None,  True),
    ChainParams("sI-THF_ion",             "sI-THF",  False, None,  True),
    ChainParams("sI-THF_ch4",            "sI-THF",  False, "CH4", False),
    ChainParams("sI-THF_ch4_ion",         "sI-THF",  False, "CH4", True),
    ChainParams("sI-THF_thf",            "sI-THF",  False, "THF", False),
    ChainParams("sI-THF_thf_ion",         "sI-THF",  False, "THF", True),
    ChainParams("sII-CH4_custom",         "sII-CH4", True,  None,  False),
    ChainParams("sII-CH4_custom_ion",     "sII-CH4", True,  None,  True),
    ChainParams("sII-CH4_custom_ch4",     "sII-CH4", True,  "CH4", False),
    ChainParams("sII-CH4_custom_ch4_ion", "sII-CH4", True,  "CH4", True),
    ChainParams("sII-CH4_custom_thf",     "sII-CH4", True,  "THF", False),
    ChainParams("sII-CH4_custom_thf_ion", "sII-CH4", True,  "THF", True),
    ChainParams("sII-CH4_ion",            "sII-CH4", False, None,  True),
    ChainParams("sII-CH4_thf",            "sII-CH4", False, "THF", False),
    ChainParams("sII-CH4_thf_ion",        "sII-CH4", False, "THF", True),
    ChainParams("sII-THF_custom_ion",     "sII-THF", True,  None,  True),
    ChainParams("sII-THF_custom_ch4",     "sII-THF", True,  "CH4", False),
    ChainParams("sII-THF_custom_ch4_ion", "sII-THF", True,  "CH4", True),
    ChainParams("sII-THF_ion",            "sII-THF", False, None,  True),
    ChainParams("sII-THF_ch4",            "sII-THF", False, "CH4", False),
    ChainParams("sII-THF_ch4_ion",        "sII-THF", False, "CH4", True),
    ChainParams("sII-THF_thf",            "sII-THF", False, "THF", False),
    ChainParams("sII-THF_thf_ion",        "sII-THF", False, "THF", True),
]


# ── Chain builder ─────────────────────────────────────────────────────────────

def _build_param_chain(params: ChainParams):
    """Build a hydrate→interface chain from ChainParams.

    Returns:
        (final_structure, writer_type) — the deepest structure and its writer type
    """
    hydrate = _HYDRATE_BUILDERS[params.hydrate_type]()
    interface = _make_slab_interface(hydrate)

    custom = None
    if params.has_custom:
        custom = _insert_custom_molecules(interface, n_molecules=3)

    solute = None
    if params.solute_type is not None:
        source = custom if custom is not None else interface
        solute = _insert_solutes(source, solute_type=params.solute_type, concentration=0.3)

    ion = None
    if params.has_ion:
        if solute is not None:
            ion = _insert_ions_from_solute(solute, concentration=0.15)
        elif custom is not None:
            ion = _insert_ions(custom, concentration=0.15)
        else:
            ion = _insert_ions(interface, concentration=0.15)

    # Return deepest non-None structure and its writer type
    if ion is not None:
        return ion, "ion"
    if solute is not None:
        return solute, "solute"
    if custom is not None:
        return custom, "custom"
    return interface, "interface"


# ── Expected molecule types ───────────────────────────────────────────────────

def _expected_top_keys(params: ChainParams) -> set[str]:
    """Compute expected [molecules] keys in .top file for given chain params."""
    keys = {"SOL"}
    # Hydrate guest (top name may have * suffix for flexible matching)
    keys.add(_HYDRATE_GUEST[params.hydrate_type][0])
    if params.has_custom:
        keys.add("etoh")  # ITP moleculetype name for custom molecule
    if params.solute_type == "CH4":
        keys.add("CH4_L")
    if params.solute_type == "THF":
        keys.add("THF_L")
    if params.has_ion:
        keys.add("NA")
        keys.add("CL")
    return keys


def _expected_gro_residues(params: ChainParams) -> set[str]:
    """Compute expected residue names in .gro file for given chain params."""
    keys = {"SOL"}
    # Hydrate guest (GRO residue name, no asterisk)
    keys.add(_HYDRATE_GUEST[params.hydrate_type][1])
    if params.has_custom:
        keys.add("MOL")  # GRO residue name for custom molecule
    if params.solute_type == "CH4":
        keys.add("CH4_L")
    if params.solute_type == "THF":
        keys.add("THF_L")
    if params.has_ion:
        keys.add("NA")
        keys.add("CL")
    return keys


# ── Writer lookup ─────────────────────────────────────────────────────────────

_WRITERS = {
    "interface": (write_interface_gro_file, write_interface_top_file),
    "custom":    (write_custom_molecule_gro_file, write_custom_molecule_top_file),
    "solute":    (write_solute_gro_file, write_solute_top_file),
    "ion":       (write_ion_gro_file, write_ion_top_file),
}


# ── Workspace fixture ─────────────────────────────────────────────────────────

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


# ── Parameterized test class ─────────────────────────────────────────────────

@gmx_skipif
class TestParametricGmxValidation:
    """Parameterized grompp validation for 27 untested chain combinations.

    Each test case:
    1. Generates a hydrate candidate from the specified hydrate type
    2. Builds an interface slab
    3. Optionally inserts custom molecules, solutes, and ions
    4. Exports GRO/TOP files using the appropriate writer
    5. Runs gmx grompp and asserts exit code 0
    6. Asserts expected molecule types in .top [molecules]
    7. Asserts expected residue names in .gro
    """

    @pytest.mark.parametrize(
        "params", CHAIN_COMBINATIONS, ids=lambda p: p.id
    )
    def test_gmx_grompp_succeeds(self, params, gmx_workspace):
        """Validate chain combination passes gmx grompp with correct molecule types."""
        # Build the chain
        final, writer_type = _build_param_chain(params)

        # Write GRO/TOP files
        gro_writer, top_writer = _WRITERS[writer_type]
        gro_path = str(gmx_workspace / f"{params.id}.gro")
        top_path = str(gmx_workspace / f"{params.id}.top")
        gro_writer(final, gro_path)
        top_writer(final, top_path)

        # Generate ion.itp if needed
        if writer_type == "ion":
            write_ion_itp(
                gmx_workspace / "ion.itp",
                final.na_count, final.cl_count,
            )

        # Copy MDP
        shutil.copy(MDP_PATH, gmx_workspace / "em.mdp")

        # Stage ITPs and assert completeness
        _stage_itp_files(top_path, gmx_workspace)
        assert_itp_completeness(top_path, gmx_workspace)

        # Run gmx grompp
        exit_code, stderr = run_gmx_grompp(
            gmx_workspace,
            gro_file=f"{params.id}.gro",
            top_file=f"{params.id}.top",
        )
        assert exit_code == 0, (
            f"gmx grompp failed for {params.id} "
            f"(hydrate={params.hydrate_type}, custom={params.has_custom}, "
            f"solute={params.solute_type}, ion={params.has_ion}):\n{stderr[-500:]}"
        )

        # Assert expected molecule types in .top [molecules]
        molecules = parse_top_molecules(top_path)
        expected_top = _expected_top_keys(params)
        for key in expected_top:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in molecules), (
                    f"Expected molecule type '{base}' or '{key}' in [molecules] "
                    f"for {params.id}, got: {list(molecules.keys())}"
                )
            else:
                assert key in molecules, (
                    f"Expected molecule type '{key}' in [molecules] "
                    f"for {params.id}, got: {list(molecules.keys())}"
                )

        # Assert expected residue names in .gro
        residue_names = parse_gro_residue_names(gro_path)
        unique_residues = set(residue_names)
        expected_gro = _expected_gro_residues(params)
        for key in expected_gro:
            if key.endswith("*"):
                base = key.rstrip("*")
                assert any(k in (base, key) for k in unique_residues), (
                    f"Expected residue '{base}' or '{key}' in .gro "
                    f"for {params.id}, got: {sorted(unique_residues)}"
                )
            else:
                assert key in unique_residues, (
                    f"Expected residue '{key}' in .gro "
                    f"for {params.id}, got: {sorted(unique_residues)}"
                )
