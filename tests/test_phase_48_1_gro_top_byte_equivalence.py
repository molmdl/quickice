"""Phase 48.1-01: SHA256 byte-equivalence tests for all 7 GROMACS export paths.

This is the WAVE 0 baseline test — captures SHA256 of file bytes for all 7
export paths (ice, interface, hydrate, ion, custom, solute, custom_guest)
BEFORE any refactor begins. The baselines are the byte-identical contract
that every subsequent wave (48.1-02 .. 48.1-14) must preserve.

Pattern: mirror ``tests/test_scancode_bugs_inserter_perf_rebuild.py:109``
(``hashlib.sha256(...).hexdigest()``) applied to file bytes instead of numpy
array bytes. The SHA256-of-file-bytes pattern is deterministic across
processes (NOT subject to PYTHONHASHSEED randomization) and across Python
versions, so the baseline is a stable contract.

Test structure
--------------
``TestGroTopByteEquivalence`` (7 parametrized cases, one per export path):
    1. Run the writer pair for this path, writing all output files to tmp_path.
    2. Stage all #include'd ITPs (matches the real CLI/GUI export behavior).
    3. Compute SHA256 of every produced .gro/.top/.itp file.
    4. Load expected SHA256s from ``baseline_shas.json`` (the authoritative
       baseline captured from the pre-refactor source in Task 2/GREEN).
    5. Assert each actual SHA256 == expected SHA256.

    RED phase (Task 1): ``baseline_shas.json`` doesn't exist yet → all 7 SKIP
    with a clear message. GREEN phase (Task 2): baseline captured → all 7 PASS.
    Subsequent waves: any byte divergence from baseline indicates the
    refactor broke byte-identical output — investigate before proceeding.

``TestGromppValidation`` (7 parametrized ``@gmx_skipif`` cases):
    1. Same export + staging as the byte-equivalence test.
    2. Run ``gmx grompp`` with ``tests/em.mdp``.
    3. Assert exit_code == 0.

    These tests prove the fixtures are physically valid (gmx accepts them) —
    they do NOT depend on ``baseline_shas.json`` (so they PASS in both RED and
    GREEN phases). Wave 9 will re-run these as the final gate.
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

# Add tests/ directory to sys.path for e2e_export_helpers import
sys.path.insert(0, str(Path(__file__).parent))

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.output.gromacs_writer import (  # noqa: E402
    write_gro_file,
    write_top_file,
    write_interface_gro_file,
    write_interface_top_file,
    write_multi_molecule_gro_file,
    write_multi_molecule_top_file,
    write_ion_gro_file,
    write_ion_top_file,
    write_custom_molecule_gro_file,
    write_custom_molecule_top_file,
    write_solute_gro_file,
    write_solute_top_file,
    get_tip4p_itp_path,
)
from quickice.structure_generation.gromacs_ion_export import write_ion_itp  # noqa: E402
from quickice.structure_generation.moleculetype_registry import MoleculetypeRegistry  # noqa: E402
from quickice.phase_mapping.lookup import lookup_phase  # noqa: E402
from quickice.structure_generation.generator import IceStructureGenerator  # noqa: E402
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.interface_builder import generate_interface  # noqa: E402
from quickice.structure_generation.ion_inserter import IonInserter  # noqa: E402
from quickice.structure_generation.solute_inserter import SoluteInserter  # noqa: E402
from quickice.structure_generation.custom_molecule_inserter import (  # noqa: E402
    CustomMoleculeInserter,
)
from quickice.structure_generation.types import (  # noqa: E402
    InterfaceStructure,
    IonConfig,
    MoleculeIndex,
    HydrateConfig,
    InterfaceConfig,
    SoluteConfig,
    CustomMoleculeConfig,
    WATER_VOLUME_NM3,
)
from e2e_export_helpers import (  # noqa: E402
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    _stage_custom_guest_itp,
    _stage_itp_files,
    _liquid_volume_nm3,
    parse_top_includes,
    run_gmx_grompp,
)


# ── Baseline paths ────────────────────────────────────────────────────────────

BASELINE_DIR = Path(
    ".planning/phases/48.1-split-gromacs-writer-dedup-gro-writers/snapshots/baseline"
)
BASELINE_SHAS_PATH = Path(
    ".planning/phases/48.1-split-gromacs-writer-dedup-gro-writers/baseline_shas.json"
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _file_sha256(path: Path) -> str:
    """SHA256 of file bytes (deterministic across processes/Python versions).

    Mirrors the pattern from ``tests/test_scancode_bugs_inserter_perf_rebuild.py:109``
    (``hashlib.sha256(arr.tobytes()).hexdigest()``) applied to file bytes.
    Unlike ``hash()``, ``hashlib.sha256`` is NOT subject to PYTHONHASHSEED
    randomization — the digest is identical across processes for the same
    input bytes.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ── Module-scoped fixtures (amortize GenIce2 ~3-5s calls) ──────────────────────
# Module scope matches the convention in tests/conftest.py (ice_ih_candidate,
# hydrate_sI_ch4_structure, interface_slab) — GenIce2 calls are expensive and
# the structures are immutable-ish (inserters return NEW structures, V-17).

# Ice candidate: 192 molecules requested → 432 actual (supercell rounding),
# shortest cell edge ~2.21 nm. This satisfies the grompp PBC rule (1.0 nm cutoff
# < half the shortest box vector = 1.10 nm). The plan suggested 16 molecules,
# but that yields a ~0.73 nm cell — too small for grompp (Rule 1 auto-fix:
# bumped to 192 to satisfy the 1.0 nm cutoff rule; documented in SUMMARY).
@pytest.fixture(scope="module")
def ice_candidate():
    """Ice Ih candidate at 250 K, 0.1 MPa (192 requested → 432 actual molecules)."""
    phase_info = lookup_phase(250, 0.1)
    gen = IceStructureGenerator(phase_info, 192)
    candidates = gen.generate_all(1)
    return candidates[0]


@pytest.fixture(scope="module")
def interface_structure(ice_candidate):
    """Slab interface from ice_candidate (3.0×3.0×8.0 nm box, seed=42)."""
    config = InterfaceConfig(
        mode="slab",
        box_x=3.0,
        box_y=3.0,
        box_z=8.0,
        seed=42,
        ice_thickness=2.0,
        water_thickness=4.0,
    )
    return generate_interface(ice_candidate, config)


@pytest.fixture(scope="module")
def hydrate_structure():
    """sI + CH4 hydrate (2×2×2 supercell, ~368 water + 64 CH4).

    The plan suggested 1×1×1, but the sI 1×1×1 cell is only 1.20 nm on each
    edge — too small for grompp's 1.0 nm cutoff (need ≥ 2.0 nm shortest edge;
    Rule 1 auto-fix: bumped to 2×2×2, shortest edge 2.40 nm, documented in
    SUMMARY)."""
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        supercell_x=2,
        supercell_y=2,
        supercell_z=2,
    )
    return gen.generate(config)


@pytest.fixture(scope="module")
def hydrate_registry():
    """MoleculetypeRegistry with CH4 registered as a hydrate guest (CH4 → CH4_H).

    Mirrors what HydrateGROMACSExporter does for the built-in ch4 path: the
    registry maps hydrate_CH4 → "CH4_H" so write_multi_molecule_top_file's
    registry branch produces "CH4_H" in [ molecules ] (matching the .gro
    residue name written by write_multi_molecule_gro_file).
    """
    reg = MoleculetypeRegistry()
    reg.register_hydrate_guest("CH4")
    return reg


@pytest.fixture(scope="module")
def ion_structure(interface_structure):
    """IonStructure from interface_structure with 0.5M NaCl, seed=42."""
    config = IonConfig(concentration_molar=0.5)
    inserter = IonInserter(config=config, seed=42)
    volume = _liquid_volume_nm3(interface_structure)
    ion_pairs = inserter.calculate_ion_pairs(0.5, volume)
    return inserter.replace_water_with_ions(interface_structure, ion_pairs)


@pytest.fixture(scope="module")
def custom_structure(interface_structure):
    """CustomMoleculeStructure from interface with 2 ethanol custom molecules, seed=42."""
    config = CustomMoleculeConfig(
        placement_mode="random",
        gro_path=ETOH_GRO,
        itp_path=ETOH_ITP,
        molecule_count=2,
    )
    inserter = CustomMoleculeInserter(config, seed=42)
    return inserter.place_random(interface_structure, 2)


@pytest.fixture(scope="module")
def solute_structure(interface_structure):
    """SoluteStructure from interface with CH4 solutes at 0.5M, seed=42."""
    config = SoluteConfig(concentration_molar=0.5, solute_type="CH4", seed=42)
    inserter = SoluteInserter(config=config, seed=42)
    return inserter.insert_solutes(interface_structure, config)


# ── Synthetic custom-guest InterfaceStructure (no GenIce2, fast) ──────────────
# Mirrors tests/test_e2e_custom_guest_cli_grompp.py:82-117 pattern:
# 2 water + 1 ethanol (17 atoms), cell 3.0 nm (satisfies grompp PBC rule:
# 1.0 nm cutoff < half shortest box vector = 1.5 nm).

_CG_ATOM_NAMES = [
    "OW", "HW1", "HW2", "MW",  # water 1
    "OW", "HW1", "HW2", "MW",  # water 2
    "H", "C", "H", "H", "C", "H", "H", "O", "H",  # ethanol (9 atoms)
]
_CG_POSITIONS = np.zeros((17, 3))
_CG_POSITIONS[:, 0] = np.linspace(0.01, 0.17, 17)
_CG_CELL = np.eye(3) * 3.0
_CG_MOLECULE_INDEX = [
    MoleculeIndex(0, 4, "water"),
    MoleculeIndex(4, 4, "water"),
    MoleculeIndex(8, 9, "etoh_e2e"),
]


@pytest.fixture(scope="module")
def interface_with_custom_guest():
    """Synthetic InterfaceStructure with 2 water + 1 ethanol (17 atoms, no GenIce2)."""
    return InterfaceStructure(
        positions=_CG_POSITIONS.copy(),
        atom_names=list(_CG_ATOM_NAMES),
        cell=_CG_CELL.copy(),
        ice_atom_count=0,
        water_atom_count=8,
        ice_nmolecules=0,
        water_nmolecules=2,
        mode="hydrate",
        report="test custom guest fixture for phase 48.1-01 baseline",
        guest_atom_count=9,
        guest_nmolecules=1,
        molecule_index=list(_CG_MOLECULE_INDEX),
    )


@pytest.fixture(scope="module")
def custom_guest_info_etoh():
    """custom_guest_info list for the synthetic ethanol guest (mol_type=etoh_e2e, MOL_H)."""
    return [
        {
            "mol_type": "etoh_e2e",
            "residue_name": "MOL_H",
            "itp_path": ETOH_ITP,
        }
    ]


# ── Per-path export + staging runners ─────────────────────────────────────────
# Each function runs the writer pair for one path, stages all #include'd ITPs
# (matching the real CLI/GUI export behavior), and returns a dict of all
# produced files {filename: Path}. Used by BOTH the byte-equivalence tests AND
# the grompp validation tests so they validate the exact same file set.


def _export_ice(out_dir: Path, ice_candidate) -> dict[str, Path]:
    """Export ice candidate → ice.gro + ice.top + tip4p-ice.itp.

    write_top_file emits an INLINE [moleculetype] SOL definition (no #include
    for tip4p-ice.itp), so no ITP staging is needed for grompp. We still copy
    tip4p-ice.itp to the output directory for the byte baseline (matches the
    plan's "ice: 3 files" expectation).
    """
    write_gro_file(ice_candidate, str(out_dir / "ice.gro"))
    write_top_file(ice_candidate, str(out_dir / "ice.top"))
    shutil.copy(get_tip4p_itp_path(), out_dir / "tip4p-ice.itp")
    return {
        "ice.gro": out_dir / "ice.gro",
        "ice.top": out_dir / "ice.top",
        "tip4p-ice.itp": out_dir / "tip4p-ice.itp",
    }


def _export_interface(out_dir: Path, interface_structure) -> dict[str, Path]:
    """Export interface → interface.gro + interface.top + #include'd ITPs."""
    write_interface_gro_file(interface_structure, str(out_dir / "interface.gro"))
    write_interface_top_file(interface_structure, str(out_dir / "interface.top"))
    # Stage all #include'd ITPs (tip4p-ice.itp; ch4_hydrate.itp if guests present)
    _stage_itp_files(str(out_dir / "interface.top"), out_dir)
    files = {
        "interface.gro": out_dir / "interface.gro",
        "interface.top": out_dir / "interface.top",
    }
    for itp in parse_top_includes(str(out_dir / "interface.top")):
        if (out_dir / itp).exists():
            files[itp] = out_dir / itp
    return files


def _export_hydrate(
    out_dir: Path, hydrate_structure, hydrate_registry
) -> dict[str, Path]:
    """Export hydrate → hydrate.gro + hydrate.top + ch4_hydrate.itp + tip4p-ice.itp."""
    write_multi_molecule_gro_file(
        hydrate_structure.positions,
        hydrate_structure.molecule_index,
        hydrate_structure.cell,
        str(out_dir / "hydrate.gro"),
        title=f"Hydrate {hydrate_structure.config.lattice_type} exported by QuickIce",
        atom_names=hydrate_structure.atom_names,
        registry=hydrate_registry,
    )
    write_multi_molecule_top_file(
        hydrate_structure.molecule_index,
        str(out_dir / "hydrate.top"),
        system_name=f"Hydrate {hydrate_structure.config.lattice_type} system",
        registry=hydrate_registry,
    )
    # Stage all #include'd ITPs (tip4p-ice.itp + ch4_hydrate.itp)
    _stage_itp_files(str(out_dir / "hydrate.top"), out_dir)
    files = {
        "hydrate.gro": out_dir / "hydrate.gro",
        "hydrate.top": out_dir / "hydrate.top",
    }
    for itp in parse_top_includes(str(out_dir / "hydrate.top")):
        if (out_dir / itp).exists():
            files[itp] = out_dir / itp
    return files


def _export_ion(out_dir: Path, ion_structure) -> dict[str, Path]:
    """Export ion → ion.gro + ion.top + ion.itp + tip4p-ice.itp.

    Note: ``na.itp`` and ``cl.itp`` do NOT exist as separate files —
    ``write_ion_itp`` generates a single ``ion.itp`` containing BOTH the NA
    and CL [moleculetype] definitions (verified at
    ``quickice/structure_generation/gromacs_ion_export.py:87``). The plan's
    "na.itp, cl.itp" description was based on a wrong assumption about
    separate ITP files; the actual file is ``ion.itp``, so this baseline
    captures 4 files (not 5). Documented as a Rule 3 auto-fix in SUMMARY.
    """
    write_ion_gro_file(ion_structure, str(out_dir / "ion.gro"))
    write_ion_top_file(ion_structure, str(out_dir / "ion.top"))
    # Generate the combined ion.itp (NA + CL in one file)
    write_ion_itp(out_dir / "ion.itp", ion_structure.na_count, ion_structure.cl_count)
    # Stage all #include'd ITPs (tip4p-ice.itp; _stage_itp_files skips ion.itp)
    _stage_itp_files(str(out_dir / "ion.top"), out_dir)
    files = {
        "ion.gro": out_dir / "ion.gro",
        "ion.top": out_dir / "ion.top",
        "ion.itp": out_dir / "ion.itp",
    }
    for itp in parse_top_includes(str(out_dir / "ion.top")):
        if itp == "ion.itp":
            continue  # Already counted above
        if (out_dir / itp).exists():
            files[itp] = out_dir / itp
    return files


def _export_custom(out_dir: Path, custom_structure) -> dict[str, Path]:
    """Export custom molecule system → custom.gro + custom.top + etoh.itp + tip4p-ice.itp."""
    write_custom_molecule_gro_file(custom_structure, str(out_dir / "custom.gro"))
    write_custom_molecule_top_file(custom_structure, str(out_dir / "custom.top"))
    # Stage all #include'd ITPs (tip4p-ice.itp + etoh.itp from custom_structure.itp_path)
    _stage_itp_files(str(out_dir / "custom.top"), out_dir)
    files = {
        "custom.gro": out_dir / "custom.gro",
        "custom.top": out_dir / "custom.top",
    }
    for itp in parse_top_includes(str(out_dir / "custom.top")):
        if (out_dir / itp).exists():
            files[itp] = out_dir / itp
    return files


def _export_solute(out_dir: Path, solute_structure) -> dict[str, Path]:
    """Export solute system → solute.gro + solute.top + ch4_liquid.itp + tip4p-ice.itp."""
    write_solute_gro_file(solute_structure, str(out_dir / "solute.gro"))
    write_solute_top_file(solute_structure, str(out_dir / "solute.top"))
    # Stage all #include'd ITPs (tip4p-ice.itp + ch4_liquid.itp)
    _stage_itp_files(str(out_dir / "solute.top"), out_dir)
    files = {
        "solute.gro": out_dir / "solute.gro",
        "solute.top": out_dir / "solute.top",
    }
    for itp in parse_top_includes(str(out_dir / "solute.top")):
        if (out_dir / itp).exists():
            files[itp] = out_dir / itp
    return files


def _export_custom_guest(
    out_dir: Path,
    interface_with_custom_guest,
    custom_guest_info_etoh,
) -> dict[str, Path]:
    """Export custom-guest interface → custom_guest.gro + custom_guest.top + etoh.itp (transformed) + tip4p-ice.itp.

    The custom-guest path requires the FULL _H transformation on etoh.itp
    (moleculetype "etoh" → "MOL_H", [atoms] resname → "MOL_H") to match the
    .top [molecules] MOL_H entry. _stage_itp_files only comments out
    [atomtypes] (under-transformed), so we additionally call
    _stage_custom_guest_itp to overwrite etoh.itp with the fully-transformed
    copy. This mirrors the pattern in tests/test_e2e_custom_guest_cli_grompp.py.
    """
    write_interface_gro_file(
        interface_with_custom_guest,
        str(out_dir / "custom_guest.gro"),
        custom_guest_info=custom_guest_info_etoh,
    )
    write_interface_top_file(
        interface_with_custom_guest,
        str(out_dir / "custom_guest.top"),
        custom_guest_info=custom_guest_info_etoh,
    )
    # Stage tip4p-ice.itp + etoh.itp (under-transformed: moleculetype "etoh")
    _stage_itp_files(str(out_dir / "custom_guest.top"), out_dir)
    # Overwrite etoh.itp with the fully-transformed copy (moleculetype "MOL_H")
    _stage_custom_guest_itp(out_dir, ETOH_ITP, "MOL")
    files = {
        "custom_guest.gro": out_dir / "custom_guest.gro",
        "custom_guest.top": out_dir / "custom_guest.top",
    }
    for itp in parse_top_includes(str(out_dir / "custom_guest.top")):
        if (out_dir / itp).exists():
            files[itp] = out_dir / itp
    return files


# ── Per-path dispatch table ───────────────────────────────────────────────────

def _run_export(
    path_name: str,
    out_dir: Path,
    *,
    ice_candidate,
    interface_structure,
    hydrate_structure,
    hydrate_registry,
    ion_structure,
    custom_structure,
    solute_structure,
    interface_with_custom_guest,
    custom_guest_info_etoh,
) -> tuple[dict[str, Path], str, str]:
    """Run the export for the given path; return (files, gro_name, top_name)."""
    if path_name == "ice":
        return _export_ice(out_dir, ice_candidate), "ice.gro", "ice.top"
    if path_name == "interface":
        return (
            _export_interface(out_dir, interface_structure),
            "interface.gro",
            "interface.top",
        )
    if path_name == "hydrate":
        return (
            _export_hydrate(out_dir, hydrate_structure, hydrate_registry),
            "hydrate.gro",
            "hydrate.top",
        )
    if path_name == "ion":
        return _export_ion(out_dir, ion_structure), "ion.gro", "ion.top"
    if path_name == "custom":
        return (
            _export_custom(out_dir, custom_structure),
            "custom.gro",
            "custom.top",
        )
    if path_name == "solute":
        return (
            _export_solute(out_dir, solute_structure),
            "solute.gro",
            "solute.top",
        )
    if path_name == "custom_guest":
        return (
            _export_custom_guest(
                out_dir, interface_with_custom_guest, custom_guest_info_etoh
            ),
            "custom_guest.gro",
            "custom_guest.top",
        )
    raise ValueError(f"Unknown path_name: {path_name!r}")


# ── Byte-equivalence tests ────────────────────────────────────────────────────


class TestGroTopByteEquivalence:
    """SHA256 byte-equivalence tests for all 7 GROMACS export paths.

    Each parametrized case runs the writer pair for its path, computes SHA256
    of every produced .gro/.top/.itp file, and asserts the SHA256s match the
    pre-refactor baseline captured in ``baseline_shas.json``.

    RED phase (Task 1): ``baseline_shas.json`` doesn't exist → all 7 SKIP.
    GREEN phase (Task 2): baseline captured → all 7 PASS.
    Subsequent waves: byte divergence indicates the refactor broke output.
    """

    @pytest.mark.parametrize(
        "path_name",
        ["ice", "interface", "hydrate", "ion", "custom", "solute", "custom_guest"],
    )
    def test_byte_equivalence(
        self,
        path_name,
        tmp_path,
        ice_candidate,
        interface_structure,
        hydrate_structure,
        hydrate_registry,
        ion_structure,
        custom_structure,
        solute_structure,
        interface_with_custom_guest,
        custom_guest_info_etoh,
    ):
        """Assert all output file bytes match the pre-refactor SHA256 baseline."""
        # RED phase: skip if baseline_shas.json not yet captured
        if not BASELINE_SHAS_PATH.exists():
            pytest.skip(
                "baseline_shas.json not yet captured — run Task 2 (GREEN) "
                "to capture the pre-refactor baseline"
            )

        # Run the export + staging for this path
        files, _gro_name, _top_name = _run_export(
            path_name,
            tmp_path,
            ice_candidate=ice_candidate,
            interface_structure=interface_structure,
            hydrate_structure=hydrate_structure,
            hydrate_registry=hydrate_registry,
            ion_structure=ion_structure,
            custom_structure=custom_structure,
            solute_structure=solute_structure,
            interface_with_custom_guest=interface_with_custom_guest,
            custom_guest_info_etoh=custom_guest_info_etoh,
        )

        # Compute actual SHA256s
        actual_shas = {fname: _file_sha256(fpath) for fname, fpath in files.items()}

        # Load expected SHA256s from baseline
        expected_shas_all = json.loads(BASELINE_SHAS_PATH.read_text())
        assert path_name in expected_shas_all, (
            f"Path '{path_name}' missing from baseline_shas.json. "
            f"Available: {sorted(expected_shas_all.keys())}"
        )
        expected_shas = expected_shas_all[path_name]

        # Assert the file set matches
        assert set(actual_shas.keys()) == set(expected_shas.keys()), (
            f"File set mismatch for path '{path_name}': "
            f"actual={sorted(actual_shas.keys())}, "
            f"expected={sorted(expected_shas.keys())}"
        )
        # Assert every file's SHA256 matches
        for fname, actual_sha in actual_shas.items():
            expected_sha = expected_shas[fname]
            assert actual_sha == expected_sha, (
                f"SHA256 mismatch for path '{path_name}' file '{fname}':\n"
                f"  actual:   {actual_sha}\n"
                f"  expected: {expected_sha}\n"
                f"The refactor changed byte-identical output — investigate "
                f"before proceeding."
            )


# ── gmx grompp validation tests ────────────────────────────────────────────────


class TestGromppValidation:
    """gmx grompp validation for all 7 GROMACS export paths.

    Each parametrized case runs the writer pair for its path, stages all
    #include'd ITPs, runs ``gmx grompp`` with ``tests/em.mdp``, and asserts
    exit_code == 0.

    These tests prove the fixtures are physically valid (gmx accepts them) —
    they do NOT depend on ``baseline_shas.json`` (so they PASS in both RED
    and GREEN phases). Wave 9 will re-run these as the final gate.
    """

    @pytest.mark.parametrize(
        "path_name",
        ["ice", "interface", "hydrate", "ion", "custom", "solute", "custom_guest"],
    )
    @gmx_skipif
    def test_grompp_succeeds(
        self,
        path_name,
        tmp_path,
        ice_candidate,
        interface_structure,
        hydrate_structure,
        hydrate_registry,
        ion_structure,
        custom_structure,
        solute_structure,
        interface_with_custom_guest,
        custom_guest_info_etoh,
    ):
        """gmx grompp exits 0 on all files exported for this path."""
        # Run the export + staging for this path
        files, gro_name, top_name = _run_export(
            path_name,
            tmp_path,
            ice_candidate=ice_candidate,
            interface_structure=interface_structure,
            hydrate_structure=hydrate_structure,
            hydrate_registry=hydrate_registry,
            ion_structure=ion_structure,
            custom_structure=custom_structure,
            solute_structure=solute_structure,
            interface_with_custom_guest=interface_with_custom_guest,
            custom_guest_info_etoh=custom_guest_info_etoh,
        )

        # Stage the MDP file (gmx grompp requires -f em.mdp)
        shutil.copy(MDP_PATH, tmp_path / "em.mdp")

        # Verify all produced files exist
        for fname, fpath in files.items():
            assert fpath.exists(), (
                f"File '{fname}' missing for path '{path_name}': {fpath}"
            )

        # Verify all #include'd ITPs are present
        top_path = str(tmp_path / top_name)
        for itp in parse_top_includes(top_path):
            assert (tmp_path / itp).exists(), (
                f"Missing #include'd ITP '{itp}' for path '{path_name}'"
            )

        # Run gmx grompp — must exit 0 (topology is self-consistent + simulation-ready)
        exit_code, stderr = run_gmx_grompp(
            tmp_path, gro_file=gro_name, top_file=top_name
        )
        assert exit_code == 0, (
            f"gmx grompp failed for path '{path_name}':\n{stderr[-1500:]}"
        )
