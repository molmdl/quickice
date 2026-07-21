"""Phase 48.1-01 baseline capture helper (NON-COLLECTED).

This is a standalone script (NOT a test_*.py file — pytest does not collect
it) that captures the authoritative SHA256 baselines for all 7 GROMACS
export paths from the CURRENT (pre-refactor) source. It mirrors the
synthetic fixtures in ``tests/test_phase_48_1_gro_top_byte_equivalence.py``
(deterministic, no GenIce2) and writes:

- ``.planning/phases/48.1-.../baseline_shas.json`` — the authoritative
  SHA256 baseline (committed to the repo; loaded by the byte-equivalence
  tests to assert byte-identical output across all subsequent waves).
- ``.planning/phases/48.1-.../snapshots/baseline/<path_name>/`` — the
  actual reference files (.gro/.top/.itp) for manual inspection.

Usage::

    python -m tests._phase_48_1_capture_baseline
    # or
    python tests/_phase_48_1_capture_baseline.py

Run ONCE to capture the pre-refactor baseline (Task 2/GREEN of plan
48.1-01). The byte-equivalence tests in
``tests/test_phase_48_1_gro_top_byte_equivalence.py`` will then PASS
against this baseline. Subsequent waves (48.1-02 .. 48.1-14) re-run the
tests to verify byte-identical output after each refactor step.

Why synthetic fixtures (not GenIce2)?
-------------------------------------
GenIce2's dipole optimization introduces run-to-run nondeterminism that
``seed=42`` does NOT control (verified: two identical
``IceStructureGenerator(...).generate_all(1)`` calls produce different
position arrays). This breaks the byte-equivalence contract — the SHA256
baseline would change every run. The fix is to use SYNTHETIC fixtures
(hardcoded positions, no GenIce2) — the same pattern used by
``tests/test_scancode_bugs_inserter_perf_rebuild.py`` for its SHA256
golden snapshots. See the Rule 1 auto-fix documentation in the SUMMARY.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure project root is on sys.path (so `from quickice...` + `from tests...` work)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
# Ensure tests/ directory is on sys.path (for e2e_export_helpers import)
_TESTS_DIR = Path(__file__).resolve().parent
if str(_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(_TESTS_DIR))

import numpy as np  # noqa: E402

from quickice.structure_generation.moleculetype_registry import (  # noqa: E402
    MoleculetypeRegistry,
)
from quickice.structure_generation.types import (  # noqa: E402
    Candidate,
    CustomMoleculeStructure,
    HydrateConfig,
    HydrateLatticeInfo,
    HydrateStructure,
    InterfaceStructure,
    IonStructure,
    MoleculeIndex,
    SoluteStructure,
)
from e2e_export_helpers import ETOH_GRO, ETOH_ITP  # noqa: E402

# Import the per-path export runners + helpers from the test module — they
# encapsulate the exact writer calls + ITP staging that the byte-equivalence
# tests verify. Also import the synthetic-position helpers so this script
# builds the SAME synthetic fixtures the test fixtures build.
from test_phase_48_1_gro_top_byte_equivalence import (  # noqa: E402
    BASELINE_DIR,
    BASELINE_SHAS_PATH,
    _file_sha256,
    _export_ice,
    _export_interface,
    _export_hydrate,
    _export_ion,
    _export_custom,
    _export_solute,
    _export_custom_guest,
    _ICE_CELL,
    _ICE_POSITIONS,
    _ICE_ATOM_NAMES,
    _ICE_NMOLECULES,
    _IFACE_CELL,
    _IFACE_POSITIONS,
    _IFACE_ATOM_NAMES,
    _IFACE_MOLECULE_INDEX,
    _HYDRATE_CELL,
    _HYDRATE_POSITIONS,
    _HYDRATE_ATOM_NAMES,
    _HYDRATE_MOLECULE_INDEX,
    _ION_CELL,
    _ION_POSITIONS,
    _ION_ATOM_NAMES,
    _ION_MOLECULE_INDEX,
    _CUSTOM_CELL,
    _CUSTOM_POSITIONS,
    _CUSTOM_ATOM_NAMES,
    _CUSTOM_MOLECULE_INDEX,
    _SOLUTE_POSITIONS,
    _SOLUTE_ATOM_NAMES,
    _SOLUTE_MOLECULE_INDICES,
    _CG_POSITIONS,
    _CG_ATOM_NAMES,
    _CG_CELL,
    _CG_MOLECULE_INDEX,
)


# ── Fixture builders (mirror the module-scoped pytest fixtures) ───────────────
# These build the SAME synthetic structures the test fixtures build, so the
# captured baseline matches what the tests verify. Deterministic (no GenIce2).


def _build_ice_candidate() -> Candidate:
    """Synthetic ice Candidate: 4 water molecules (12 atoms) in a 3.0 nm box."""
    return Candidate(
        positions=_ICE_POSITIONS.copy(),
        atom_names=list(_ICE_ATOM_NAMES),
        cell=_ICE_CELL.copy(),
        nmolecules=_ICE_NMOLECULES,
        phase_id="ice_ih_synth",
        seed=42,
    )


def _build_interface_structure() -> InterfaceStructure:
    """Synthetic InterfaceStructure: 2 ice + 4 water = 22 atoms in 3.0×3.0×8.0 nm."""
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


def _build_hydrate_structure() -> HydrateStructure:
    """Synthetic HydrateStructure: 2 water + 1 CH4 = 13 atoms in a 3.0 nm box."""
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


def _build_hydrate_registry() -> MoleculetypeRegistry:
    """MoleculetypeRegistry with CH4 registered as a hydrate guest (CH4 → CH4_H)."""
    reg = MoleculetypeRegistry()
    reg.register_hydrate_guest("CH4")
    return reg


def _build_ion_structure() -> IonStructure:
    """Synthetic IonStructure: 2 water + 1 NA + 1 CL = 10 atoms in a 3.0 nm box."""
    return IonStructure(
        positions=_ION_POSITIONS.copy(),
        atom_names=list(_ION_ATOM_NAMES),
        cell=_ION_CELL.copy(),
        molecule_index=list(_ION_MOLECULE_INDEX),
        na_count=1,
        cl_count=1,
        report="synthetic ion for phase 48.1-01 baseline",
    )


def _build_custom_structure() -> CustomMoleculeStructure:
    """Synthetic CustomMoleculeStructure: 2 water + 1 ethanol = 17 atoms in 3.0 nm."""
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


def _build_solute_structure(interface_structure: InterfaceStructure) -> SoluteStructure:
    """Synthetic SoluteStructure: interface (22 atoms) + 1 CH4 solute (5 atoms)."""
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


def _build_interface_with_custom_guest() -> InterfaceStructure:
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


def _build_custom_guest_info_etoh() -> list[dict]:
    """custom_guest_info list for the synthetic ethanol guest."""
    return [
        {
            "mol_type": "etoh_e2e",
            "residue_name": "MOL_H",
            "itp_path": ETOH_ITP,
        }
    ]


# ── Capture entrypoint ────────────────────────────────────────────────────────


def capture_baselines(output_dir: Path, shas_path: Path) -> dict:
    """Run all 7 export paths, write files to output_dir, compute SHA256s, save JSON.

    For each path: run the writers + ITP staging (reusing the test module's
    ``_export_*`` functions), compute ``_file_sha256`` for each produced file,
    save the dict ``{path_name: {filename: sha256}}`` to ``shas_path`` as JSON.
    Also copy the actual files to ``output_dir/<path_name>/`` for manual
    inspection (the snapshots/baseline/ directory).

    Returns the captured dict (also written to ``shas_path``).
    """
    # Build all synthetic fixtures ONCE (no GenIce2, <1ms total)
    print("[capture] Building synthetic fixtures (no GenIce2, deterministic)...")
    ice_candidate = _build_ice_candidate()
    interface_structure = _build_interface_structure()
    hydrate_structure = _build_hydrate_structure()
    hydrate_registry = _build_hydrate_registry()
    ion_structure = _build_ion_structure()
    custom_structure = _build_custom_structure()
    solute_structure = _build_solute_structure(interface_structure)
    interface_with_custom_guest = _build_interface_with_custom_guest()
    custom_guest_info_etoh = _build_custom_guest_info_etoh()
    print("[capture] Fixtures built.")

    # Per-path export + SHA256 capture
    all_shas: dict[str, dict[str, str]] = {}
    import tempfile

    with tempfile.TemporaryDirectory(prefix="phase48_1_baseline_") as tmp:
        tmp_dir = Path(tmp)

        path_runs = [
            ("ice", lambda d: _export_ice(d, ice_candidate)),
            ("interface", lambda d: _export_interface(d, interface_structure)),
            (
                "hydrate",
                lambda d: _export_hydrate(d, hydrate_structure, hydrate_registry),
            ),
            ("ion", lambda d: _export_ion(d, ion_structure)),
            ("custom", lambda d: _export_custom(d, custom_structure)),
            ("solute", lambda d: _export_solute(d, solute_structure)),
            (
                "custom_guest",
                lambda d: _export_custom_guest(
                    d, interface_with_custom_guest, custom_guest_info_etoh
                ),
            ),
        ]

        for path_name, export_fn in path_runs:
            # Each path gets its own subdirectory in tmp (clean state)
            path_tmp = tmp_dir / path_name
            path_tmp.mkdir(parents=True, exist_ok=True)
            print(f"[capture] Exporting path '{path_name}'...")
            files = export_fn(path_tmp)
            # Compute SHA256 for each produced file
            shas = {fname: _file_sha256(fpath) for fname, fpath in files.items()}
            all_shas[path_name] = shas
            print(
                f"[capture]   {path_name}: {len(shas)} files -> "
                f"{sorted(shas.keys())}"
            )

            # Copy files to the snapshot directory for manual inspection
            snapshot_dir = output_dir / path_name
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            for fname, fpath in files.items():
                import shutil

                shutil.copy2(fpath, snapshot_dir / fname)

    # Write the baseline JSON
    shas_path.parent.mkdir(parents=True, exist_ok=True)
    shas_path.write_text(json.dumps(all_shas, indent=2, sort_keys=True) + "\n")
    print(f"[capture] Wrote baseline SHA256s to {shas_path}")
    print(f"[capture] Wrote snapshot files to {output_dir}")
    return all_shas


def _verify_expected_file_counts(all_shas: dict) -> None:
    """Verify the captured JSON has the expected file counts per path.

    Expected (post-Rule-1-auto-fix for ion: na.itp+cl.itp -> ion.itp):
        ice: 3, interface: 3, hydrate: 4, ion: 4, custom: 4, solute: 4, custom_guest: 4
    """
    expected = {
        "ice": 3,          # ice.gro, ice.top, tip4p-ice.itp
        "interface": 3,    # interface.gro, interface.top, tip4p-ice.itp
        "hydrate": 4,      # hydrate.gro, hydrate.top, ch4_hydrate.itp, tip4p-ice.itp
        "ion": 4,          # ion.gro, ion.top, ion.itp, tip4p-ice.itp (NOT 5: na+cl combined)
        "custom": 4,       # custom.gro, custom.top, etoh.itp, tip4p-ice.itp
        "solute": 4,       # solute.gro, solute.top, ch4_liquid.itp, tip4p-ice.itp
        "custom_guest": 4,  # custom_guest.gro, custom_guest.top, etoh.itp, tip4p-ice.itp
    }
    all_ok = True
    for path_name, expected_count in expected.items():
        actual_count = len(all_shas.get(path_name, {}))
        if actual_count != expected_count:
            print(
                f"[capture] WARNING: path '{path_name}' has {actual_count} files, "
                f"expected {expected_count}: {sorted(all_shas.get(path_name, {}).keys())}"
            )
            all_ok = False
        else:
            print(
                f"[capture] OK: path '{path_name}' has {actual_count} files (matches expected)"
            )
    return all_ok


def main() -> int:
    """Capture baselines and verify file counts. Returns 0 on success."""
    print(f"[capture] BASELINE_DIR = {BASELINE_DIR}")
    print(f"[capture] BASELINE_SHAS_PATH = {BASELINE_SHAS_PATH}")
    all_shas = capture_baselines(BASELINE_DIR, BASELINE_SHAS_PATH)
    print()
    print("[capture] Verifying expected file counts per path:")
    _verify_expected_file_counts(all_shas)
    print()
    print("[capture] Baseline capture complete.")
    print(f"[capture] Total paths: {len(all_shas)}")
    print(f"[capture] Total files: {sum(len(v) for v in all_shas.values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
