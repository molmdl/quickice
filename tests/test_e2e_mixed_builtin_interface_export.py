"""Regression test (gap G3, RESEARCH-INVENTORY §4): MIXED built-in CH4+THF
slab interface export through BOTH pipeline surfaces — the GUI
``InterfaceGROMACSExporter`` (INTERFACE tab) AND the CLI ``_run_export_step``
interface branch.

Commit b278a9ed (2026-08-11, UAT-F Issue 3) fixed the mixed built-in CH4+THF
interface export — the single ``detect_guest_type_from_atoms`` pass on the
whole guest region mislabeling ALL 1296 cage guests as CH4_H (864x5 + 432x13)
— but shipped touching ONLY ``quickice/output/guest_info.py`` +
``quickice/output/interface_writer.py`` with NO regression test. Mixed CH4+THF
exports were previously covered via the GUI HYDRATE exporter
(test_e2e_mixed_lattice_gui.py — multi-molecule writers) and the ion exporter
only — never through ``write_interface_top_file`` / InterfaceGROMACSExporter
with a CH4+THF hydrate slab. This file closes that gap: a fix that landed with
zero e2e now has a permanent regression guard on both export surfaces.

What the b278a9ed fix does (and what these tests lock in):

  * ``write_interface_top_file`` detects the mixed built-in case via
    ``guest_atom_counts`` (2+ built-in types) and run-length encodes
    ``[ molecules ]`` as CH4_H/THF_H runs, ``#include``-ing BOTH
    ``ch4_hydrate.itp`` and ``thf_hydrate.itp``;
  * ``_stage_hydrate_guest_itps`` (GUI exporters) stages built-in ITPs from
    the hydrate config's ``cage_guest_assignments`` (authoritative) instead
    of the single-pass atom detection;
  * the CLI interface branch (``copy_itp_files_for_structure``,
    ``quickice/cli/itp_helpers.py``) stages every distinct built-in
    ``{type}_hydrate.itp`` from the config for the same reason (48.3-05
    follow-up — the CLI staging had the SAME single-type gap:
    ``_detect_guest_type`` returned None for mixed slabs because the average
    atoms/guest (9936/1296 = 7.67) falls BETWEEN the ch4=5 and thf=13
    thresholds, so NEITHER guest ITP was staged while the .top ``#include``d
    both -> grompp fatal "File not found").

Sensitivity note (why BOTH names are asserted everywhere): a regression to
the pre-b278a9ed single-detect pass mislabels every guest CH4_H — the .gro
loses THF_H residues AND the .top loses the THF_H ``[ molecules ]`` entries
and the ``thf_hydrate.itp`` ``#include``. Asserting BOTH CH4_H and THF_H in
``[ molecules ]`` + .gro residues + staged ITPs catches that class at the
file level even before grompp runs; a single-name-only assertion would not.

Fixture: module-scoped GenIce2 sII hydrate with mixed BUILT-IN occupancy
(CH4 in the 16 small cages + THF in the 8 large cages per unit cell, via
``HydrateConfig.cage_guest_assignments`` — NO custom molecules: the whole
point is that a single detect pass must label BOTH types). Each export leg
derives a FRESH slab interface via ``to_candidate`` + ``assemble_slab``
(44.1-19 discipline — build a fresh interface per export leg; exporters may
mutate structure state). Box >= 3 nm shortest vector (grompp PBC rule:
cutoff 1.0 < half the shortest box vector — STATE [41-10]); the proven sII
mixed-slab box from tests/test_e2e_custom_guest_mixed_cage_interface.py is
reused.

``QT_QPA_PLATFORM=offscreen`` is required for the GUI leg (headless machine);
``QFileDialog.getSaveFileName`` is patched (it returns ``("", "")`` under
offscreen -> the exporter returns False without writing — Pattern B, patching
the USING module's namespace ``quickice.gui.export``). ``gmx`` is on PATH here
so grompp runs (``@gmx_skipif`` skips when absent; the file-level asserts
precede grompp and catch the mislabeling class on their own).
"""

import shutil
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from tests.conftest import gmx_skipif
from tests.e2e_export_helpers import (
    MDP_PATH,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_includes,
    parse_top_molecules,
    run_gmx_grompp,
)
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.types import (  # noqa: E402
    CageGuestAssignment,
    HydrateConfig,
    InterfaceConfig,
)


# Proven sII mixed-slab box (mirrors tests/test_e2e_custom_guest_mixed_cage_
# interface.py): shortest box vector 5.13629 nm > 2 * rcoulomb = 2.0 nm
# (grompp PBC rule — STATE [41-10]).
_SLAB_BOX_KWARGS = dict(
    box_x=5.13629,
    box_y=5.13629,
    box_z=10.57382,
    ice_thickness=5.13629,
    water_thickness=5.43753,
    seed=42,
)


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: mixed built-in (CH4 small + THF large) sII hydrate
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def mixed_builtin_sii_hydrate():
    """Module-scoped: the mixed built-in sII hydrate built ONCE (GenIce2
    amortization across all tests in this module — AGENTS.md convention).

    Mirrors the fixture style of tests/test_e2e_mixed_lattice_gui.py:
    ``cage_guest_assignments`` places BUILT-IN ch4 in the small cages and
    BUILT-IN thf in the large cages (occupancy 100% both). NO custom
    molecules anywhere in this module — the regression target is precisely
    that a single detect pass must label BOTH built-in types.

    Returns ``SimpleNamespace(hydrate=..., config=...)``. ``config`` is the
    ``HydrateConfig`` the real GUI flow passes to
    ``export_interface_gromacs(hydrate_config=...)``
    (main_window.py:1795-1797) and the real CLI flow reads via
    ``self._hydrate_result.config`` — both staging paths are config-driven.
    """
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sII",
        guest_type="ch4",  # primary (legacy) field — ch4 is built-in
        cage_guest_assignments={
            "small": CageGuestAssignment(guest_type="ch4", occupancy=100.0),
            "large": CageGuestAssignment(guest_type="thf", occupancy=100.0),
        },
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    # Sanity: mixed built-in must place BOTH guest types.
    assert hydrate.guest_count > 0, (
        f"mixed built-in sII should have cage guests, got "
        f"guest_count={hydrate.guest_count}"
    )
    mol_types = {m.mol_type for m in hydrate.molecule_index}
    assert "ch4" in mol_types and "thf" in mol_types, (
        f"mixed built-in sII should place BOTH ch4 + thf, got "
        f"mol_types={mol_types}"
    )
    return SimpleNamespace(hydrate=hydrate, config=config)


def _fresh_mixed_slab(hydrate):
    """Derive a FRESH slab interface from the hydrate (one per export leg).

    44.1-19 discipline: exporters may mutate structure state, so each export
    leg gets its own ``to_candidate()`` + ``assemble_slab()`` (cheap — the
    expensive GenIce2 call is amortized in the module fixture).
    """
    candidate = hydrate.to_candidate()
    iface = assemble_slab(
        candidate, InterfaceConfig(mode="slab", **_SLAB_BOX_KWARGS)
    )
    assert iface.guest_nmolecules > 0, "mixed slab should have cage guests"
    return iface


# ══════════════════════════════════════════════════════════════════════════════
# Task 1 sanity: fixture carries BOTH built-in guest types (always runs)
# ══════════════════════════════════════════════════════════════════════════════


def test_mixed_slab_fixture_has_both_builtin_guest_types(
    mixed_builtin_sii_hydrate,
):
    """Fixture sanity (no gmx needed): the mixed built-in sII hydrate carries
    BOTH ch4 + thf cage guests, and the fresh slab interface inherits the
    per-type ``guest_atom_counts`` {ch4: 5, thf: 13} — the descriptor data the
    b278a9ed writer path needs to detect the mixed built-in case.

    Also locks the grompp PBC precondition (box >= 3 nm shortest vector) and
    the built-in-only contract (``is_custom`` False — no custom molecules).
    """
    ns = mixed_builtin_sii_hydrate

    # Hydrate-level metadata: per-type atom counts for BOTH built-ins.
    candidate = ns.hydrate.to_candidate()
    assert candidate.metadata["guest_atom_counts"] == {"ch4": 5, "thf": 13}, (
        f"mixed built-in sII metadata must carry BOTH guest types, got "
        f"{candidate.metadata.get('guest_atom_counts')}"
    )

    # Fresh slab interface (the per-leg derivation under test).
    iface = _fresh_mixed_slab(ns.hydrate)
    assert iface.guest_atom_counts == {"ch4": 5, "thf": 13}, (
        f"mixed slab must inherit per-type guest_atom_counts, got "
        f"{iface.guest_atom_counts}"
    )
    descriptors = {d.mol_type: d for d in iface.guest_descriptors}
    assert "ch4" in descriptors and "thf" in descriptors, (
        f"mixed slab descriptors must cover BOTH built-ins, got "
        f"{sorted(descriptors)}"
    )
    assert not any(d.is_custom for d in descriptors.values()), (
        "NO custom molecules in this test — built-in CH4+THF only (the "
        "point: a single detect pass must label BOTH types)"
    )

    # grompp PBC rule (STATE [41-10]): cutoff 1.0 nm < half the shortest box
    # vector -> every box vector must be >= 3.0 nm.
    shortest = min(
        iface.cell[0, 0], iface.cell[1, 1], iface.cell[2, 2]
    )
    assert shortest >= 3.0, (
        f"slab box shortest vector {shortest} nm < 3.0 nm — grompp would "
        f"fatal-error with 'cut-off longer than half the shortest box vector'"
    )
