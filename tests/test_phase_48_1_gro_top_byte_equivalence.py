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
from quickice.structure_generation.types import (  # noqa: E402
    InterfaceStructure,
    MoleculeIndex,
)
from e2e_export_helpers import (  # noqa: E402
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    _stage_custom_guest_itp,
    _stage_itp_files,
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


# ── Synthetic deterministic fixtures (NO GenIce2 — byte-identical across runs) ─
# Rule 1 auto-fix: the plan assumed ``seed=42`` would make GenIce2 deterministic,
# but GenIce2's dipole optimization introduces run-to-run nondeterminism that
# the seed does NOT control (verified: two ``IceStructureGenerator(...).generate_all(1)``
# calls with identical args produce different position arrays). This breaks the
# byte-equivalence contract — the SHA256 baseline would change every run.
#
# Fix: use SYNTHETIC fixtures (hardcoded positions, no GenIce2) — the same
# pattern used by ``tests/test_scancode_bugs_inserter_perf_rebuild.py`` for its
# SHA256 golden snapshots. The synthetic fixtures are minimal but exercise every
# writer code path (ice 3→4 MW expansion, water 4-atom pass-through, guest
# detect+reorder, ion NA/CL formatting, custom molecule, solute). Box sizes
# ≥ 3.0 nm on every edge satisfy grompp's PBC rule (1.0 nm cutoff < half the
# shortest box vector = 1.5 nm). Documented in SUMMARY.
#
# Module scope is safe: the structures are immutable (no inserter mutates them;
# V-17 fix), and the synthetic construction is cheap (no GenIce2 calls, <1ms).

# Water geometry helpers (O-H ≈ 0.0957 nm, TIP4P-ICE settle DOH).
_OH_DIST = 0.0957   # nm (O-H bond length, TIP4P-ICE settle doh)
_HH_DIST = 0.15139  # nm (H-H distance, TIP4P-ICE settle dhh — for reference)
_TIP4P_ALPHA = 0.13458335  # MW virtual-site coefficient


def _water_3atom(cx: float, cy: float, cz: float) -> list[list[float]]:
    """Build a 3-atom water molecule (O, H, H) centered near (cx, cy, cz)."""
    return [
        [cx, cy, cz],                 # O
        [cx + _OH_DIST, cy, cz],      # H1
        [cx, cy + _OH_DIST, cz],      # H2
    ]


def _water_4atom(cx: float, cy: float, cz: float) -> list[list[float]]:
    """Build a 4-atom TIP4P water molecule (OW, HW1, HW2, MW) near (cx, cy, cz).

    MW = O + α*(H1-O) + α*(H2-O) (compute_mw_position formula, line 1113).
    """
    mw_x = cx + _TIP4P_ALPHA * _OH_DIST
    mw_y = cy + _TIP4P_ALPHA * _OH_DIST
    return [
        [cx, cy, cz],                 # OW
        [cx + _OH_DIST, cy, cz],      # HW1
        [cx, cy + _OH_DIST, cz],      # HW2
        [mw_x, mw_y, cz],             # MW (virtual site)
    ]


def _ch4_5atom(cx: float, cy: float, cz: float) -> list[list[float]]:
    """Build a 5-atom CH4 molecule (C, H, H, H, H) centered near (cx, cy, cz)."""
    d = 0.109  # C-H bond length (~1.09 Å = 0.109 nm)
    return [
        [cx, cy, cz],                       # C
        [cx + d, cy, cz],                   # H
        [cx - d / 3, cy + d, cz],           # H
        [cx - d / 3, cy - d / 2, cz + d],   # H
        [cx - d / 3, cy - d / 2, cz - d],   # H
    ]


def _ethanol_9atom(cx: float, cy: float, cz: float) -> list[list[float]]:
    """Build a 9-atom ethanol molecule (H, C, H, H, C, H, H, O, H) near (cx, cy, cz).

    Atom order matches the etoh.gro/etoh.itp convention used by the custom guest
    fixture in tests/test_e2e_custom_guest_cli_grompp.py (9 atoms). Positions
    are approximate — grompp uses the ITP bond/angle definitions, not the
    exact .gro geometry.
    """
    return [
        [cx, cy, cz],                       # H
        [cx + 0.15, cy, cz],                # C
        [cx, cy + 0.1, cz],                 # H
        [cx, cy, cz + 0.1],                 # H
        [cx + 0.30, cy + 0.1, cz],          # C
        [cx + 0.40, cy + 0.05, cz],         # H
        [cx + 0.32, cy + 0.20, cz],         # H
        [cx + 0.25, cy - 0.10, cz],         # O
        [cx + 0.20, cy - 0.15, cz],         # H
    ]


# ── Ice candidate (Candidate): 4 water molecules × 3 atoms = 12 atoms ────────
# Cell 3.0×3.0×3.0 nm (shortest edge 3.0 > 2×1.0 nm cutoff → grompp-safe).

_ICE_CELL = np.eye(3) * 3.0
_ICE_POSITIONS = np.array(
    _water_3atom(0.5, 0.5, 0.5)
    + _water_3atom(1.5, 0.5, 0.5)
    + _water_3atom(0.5, 1.5, 0.5)
    + _water_3atom(1.5, 1.5, 0.5),
    dtype=float,
)
_ICE_ATOM_NAMES = ["O", "H", "H"] * 4
_ICE_NMOLECULES = 4


@pytest.fixture(scope="module")
def ice_candidate():
    """Synthetic ice Candidate: 4 water molecules (12 atoms) in a 3.0 nm box.

    Deterministic (no GenIce2) — the SHA256 baseline is reproducible across
    runs. Exercises write_gro_file's 3→4 atom MW expansion + write_top_file's
    inline [moleculetype] SOL definition.
    """
    from quickice.structure_generation.types import Candidate
    return Candidate(
        positions=_ICE_POSITIONS.copy(),
        atom_names=list(_ICE_ATOM_NAMES),
        cell=_ICE_CELL.copy(),
        nmolecules=_ICE_NMOLECULES,
        phase_id="ice_ih_synth",
        seed=42,
    )


# ── Interface (InterfaceStructure): 2 ice + 4 water = 22 atoms ───────────────
# Cell 3.0×3.0×8.0 nm (slab: ice at bottom, water in middle — simplified to
# ice then water; mode="slab" for the title string).

_IFACE_CELL = np.diag([3.0, 3.0, 8.0])
_IFACE_POSITIONS = np.array(
    _water_3atom(0.5, 0.5, 0.5)
    + _water_3atom(1.5, 0.5, 0.5)            # 2 ice molecules (6 atoms, 3-atom OHH)
    + _water_4atom(0.5, 0.5, 4.0)
    + _water_4atom(1.5, 0.5, 4.0)
    + _water_4atom(0.5, 1.5, 4.0)
    + _water_4atom(1.5, 1.5, 4.0),           # 4 water molecules (16 atoms, 4-atom TIP4P)
    dtype=float,
)
_IFACE_ATOM_NAMES = (
    ["O", "H", "H"] * 2                       # 2 ice molecules (3-atom)
    + ["OW", "HW1", "HW2", "MW"] * 4          # 4 water molecules (4-atom TIP4P)
)
_IFACE_MOLECULE_INDEX = [
    MoleculeIndex(0, 3, "ice"),
    MoleculeIndex(3, 3, "ice"),
    MoleculeIndex(6, 4, "water"),
    MoleculeIndex(10, 4, "water"),
    MoleculeIndex(14, 4, "water"),
    MoleculeIndex(18, 4, "water"),
]


@pytest.fixture(scope="module")
def interface_structure():
    """Synthetic InterfaceStructure: 2 ice (6 atoms) + 4 water (16 atoms) = 22 atoms.

    Deterministic (no GenIce2). Exercises write_interface_gro_file's ice 3→4
    MW expansion + water 4-atom pass-through + write_interface_top_file's
    #include "tip4p-ice.itp" (no guests → no ch4_hydrate.itp #include).
    """
    return InterfaceStructure(
        positions=_IFACE_POSITIONS.copy(),
        atom_names=list(_IFACE_ATOM_NAMES),
        cell=_IFACE_CELL.copy(),
        ice_atom_count=6,
        water_atom_count=16,
        ice_nmolecules=2,
        water_nmolecules=4,
        mode="slab",
        report="synthetic interface for phase 48.1-01 baseline",
        guest_atom_count=0,
        guest_nmolecules=0,
        molecule_index=list(_IFACE_MOLECULE_INDEX),
    )


# ── Hydrate (HydrateStructure): 2 water + 1 CH4 = 13 atoms ────────────────────
# Cell 3.0×3.0×3.0 nm. Uses MoleculetypeRegistry to register CH4 → CH4_H.

_HYDRATE_CELL = np.eye(3) * 3.0
_HYDRATE_POSITIONS = np.array(
    _water_4atom(0.5, 0.5, 0.5)
    + _water_4atom(1.5, 1.5, 0.5)            # 2 water molecules (8 atoms)
    + _ch4_5atom(1.0, 1.0, 1.5),            # 1 CH4 molecule (5 atoms)
    dtype=float,
)
_HYDRATE_ATOM_NAMES = (
    ["OW", "HW1", "HW2", "MW"] * 2           # 2 water molecules
    + ["C", "H", "H", "H", "H"]              # 1 CH4 molecule
)
_HYDRATE_MOLECULE_INDEX = [
    MoleculeIndex(0, 4, "water"),
    MoleculeIndex(4, 4, "water"),
    MoleculeIndex(8, 5, "ch4"),
]


@pytest.fixture(scope="module")
def hydrate_structure():
    """Synthetic HydrateStructure: 2 water (8 atoms) + 1 CH4 (5 atoms) = 13 atoms.

    Deterministic (no GenIce2). Exercises write_multi_molecule_gro_file's
    per-molecule loop + reorder_guest_atoms (ch4 C-first reordering) +
    write_multi_molecule_top_file's registry-driven res_name + #include.
    """
    from quickice.structure_generation.types import (
        HydrateConfig, HydrateStructure, HydrateLatticeInfo,
    )
    config = HydrateConfig(
        lattice_type="sI",
        guest_type="ch4",
        supercell_x=1, supercell_y=1, supercell_z=1,
    )
    lattice_info = HydrateLatticeInfo.from_lattice_type("sI")
    return HydrateStructure(
        positions=_HYDRATE_POSITIONS.copy(),
        atom_names=list(_HYDRATE_ATOM_NAMES),
        cell=_HYDRATE_CELL.copy(),
        molecule_index=list(_HYDRATE_MOLECULE_INDEX),
        config=config,
        lattice_info=lattice_info,
        report="synthetic hydrate for phase 48.1-01 baseline",
        guest_count=1,
        water_count=2,
    )


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


# ── Ion (IonStructure): 2 water + 1 NA + 1 CL = 10 atoms ──────────────────────
# Cell 3.0×3.0×3.0 nm.

_ION_CELL = np.eye(3) * 3.0
_ION_POSITIONS = np.array(
    _water_4atom(0.5, 0.5, 0.5)
    + _water_4atom(1.5, 1.5, 0.5)            # 2 water molecules (8 atoms)
    + [[2.0, 2.0, 0.5]]                      # 1 NA ion
    + [[2.5, 2.5, 0.5]],                     # 1 CL ion
    dtype=float,
)
_ION_ATOM_NAMES = (
    ["OW", "HW1", "HW2", "MW"] * 2           # 2 water molecules
    + ["NA", "CL"]                           # 1 NA + 1 CL
)
_ION_MOLECULE_INDEX = [
    MoleculeIndex(0, 4, "water"),
    MoleculeIndex(4, 4, "water"),
    MoleculeIndex(8, 1, "na"),
    MoleculeIndex(9, 1, "cl"),
]


@pytest.fixture(scope="module")
def ion_structure():
    """Synthetic IonStructure: 2 water (8 atoms) + 1 NA + 1 CL = 10 atoms.

    Deterministic (no GenIce2, no IonInserter). Exercises write_ion_gro_file's
    SOL + NA + CL formatting + write_ion_top_file's #include "ion.itp" +
    write_ion_itp's combined NA+CL [moleculetype] generation.
    """
    from quickice.structure_generation.types import IonStructure
    return IonStructure(
        positions=_ION_POSITIONS.copy(),
        atom_names=list(_ION_ATOM_NAMES),
        cell=_ION_CELL.copy(),
        molecule_index=list(_ION_MOLECULE_INDEX),
        na_count=1,
        cl_count=1,
        report="synthetic ion for phase 48.1-01 baseline",
    )


# ── Custom molecule (CustomMoleculeStructure): 2 water + 1 ethanol = 17 atoms ─
# Cell 3.0×3.0×3.0 nm. The "custom" molecule is the user-provided ethanol (NOT a
# hydrate cage guest — that's the separate custom_guest path).

_CUSTOM_CELL = np.eye(3) * 3.0
_CUSTOM_POSITIONS = np.array(
    _water_4atom(0.5, 0.5, 0.5)
    + _water_4atom(1.5, 1.5, 0.5)            # 2 water molecules (8 atoms)
    + _ethanol_9atom(1.0, 1.0, 1.5),          # 1 custom ethanol (9 atoms)
    dtype=float,
)
_CUSTOM_ATOM_NAMES = (
    ["OW", "HW1", "HW2", "MW"] * 2           # 2 water molecules
    + ["H", "C", "H", "H", "C", "H", "H", "O", "H"]  # 1 ethanol (9 atoms)
)
_CUSTOM_MOLECULE_INDEX = [
    MoleculeIndex(0, 4, "water"),
    MoleculeIndex(4, 4, "water"),
    MoleculeIndex(8, 9, "custom"),
]


@pytest.fixture(scope="module")
def custom_structure():
    """Synthetic CustomMoleculeStructure: 2 water (8 atoms) + 1 ethanol (9 atoms) = 17 atoms.

    Deterministic (no GenIce2, no CustomMoleculeInserter). Exercises
    write_custom_molecule_gro_file's SOL + custom formatting +
    write_custom_molecule_top_file's #include "etoh.itp" + custom atomtype merge.
    """
    from quickice.structure_generation.types import CustomMoleculeStructure
    return CustomMoleculeStructure(
        positions=_CUSTOM_POSITIONS.copy(),
        atom_names=list(_CUSTOM_ATOM_NAMES),
        cell=_CUSTOM_CELL.copy(),
        molecule_index=list(_CUSTOM_MOLECULE_INDEX),
        ice_atom_count=0,
        water_atom_count=8,
        custom_molecule_atom_count=9,
        ice_nmolecules=0,
        water_nmolecules=2,
        config=None,
        moleculetype_name="MOL",
        gro_path=ETOH_GRO,
        itp_path=ETOH_ITP,
        residue_name="MOL",
        custom_molecule_count=1,
    )


# ── Solute (SoluteStructure): interface (22 atoms) + 1 CH4 solute (5 atoms) ───
# Uses the synthetic interface_structure as the source. The solute CH4 is a
# separate positions array (5 atoms: C, H, H, H, H).

_SOLUTE_POSITIONS = np.array(_ch4_5atom(1.0, 1.0, 6.0), dtype=float)
_SOLUTE_ATOM_NAMES = ["C", "H", "H", "H", "H"]
_SOLUTE_MOLECULE_INDICES = [(0, 5)]


@pytest.fixture(scope="module")
def solute_structure(interface_structure):
    """Synthetic SoluteStructure: interface (22 atoms) + 1 CH4 solute (5 atoms).

    Deterministic (no GenIce2, no SoluteInserter). Exercises
    write_solute_gro_file's SOL + solute formatting + write_solute_top_file's
    #include "ch4_liquid.itp" + registry-driven CH4_L moleculetype name.
    """
    from quickice.structure_generation.types import SoluteStructure
    registry = MoleculetypeRegistry()
    registry.register_liquid_solute("CH4")  # maps liquid_CH4 → "CH4_L"
    return SoluteStructure(
        positions=_SOLUTE_POSITIONS.copy(),
        atom_names=list(_SOLUTE_ATOM_NAMES),
        cell=interface_structure.cell.copy(),
        solute_type="CH4",
        n_molecules=1,
        molecule_indices=list(_SOLUTE_MOLECULE_INDICES),
        registry=registry,
        interface_structure=interface_structure,
        ice_nmolecules=interface_structure.ice_nmolecules,
        water_nmolecules=interface_structure.water_nmolecules,
    )


# ── Synthetic custom-guest InterfaceStructure (no GenIce2, fast) ──────────────
# Mirrors tests/test_e2e_custom_guest_cli_grompp.py:82-117 pattern:
# 2 water + 1 ethanol (17 atoms), cell 3.0 nm (satisfies grompp PBC rule:
# 1.0 nm cutoff < half shortest box vector = 1.5 nm).

_CG_ATOM_NAMES = [
    "OW", "HW1", "HW2", "MW",  # water 1
    "OW", "HW1", "HW2", "MW",  # water 2
    "H", "C", "H", "H", "C", "H", "H", "O", "H",  # ethanol (9 atoms)
]
_CG_POSITIONS = np.array(
    _water_4atom(0.5, 0.5, 0.5)
    + _water_4atom(1.5, 0.5, 0.5)
    + _ethanol_9atom(1.0, 1.0, 1.5),
    dtype=float,
)
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
        report="synthetic custom guest fixture for phase 48.1-01 baseline",
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
