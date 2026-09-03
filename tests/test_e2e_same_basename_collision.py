"""G2 regression: SAME-basename collision — etoh as BOTH cage guest AND liquid custom molecule.

NO cmet pre-renaming — the collision IS the scenario.  This is the exact real-user
input (UAT Issue 2 / P2 fixture-sanitization class): the user uploads the SAME
``etoh.gro``/``etoh.itp`` pair as the hydrate cage guest (Tab 1) AND as the liquid
custom molecule (Tab 3).  The three pre-existing cross-tab e2e tests deliberately
renamed the liquid copy to ``cmet.gro/cmet.itp`` "to avoid the etoh.itp filename
collision" — the fixture pre-solved the exact UX scenario that bites real users,
which is why the duplicate-#include bug (both ITPs staged as ``etoh.itp``, the
cage-guest MOL_H copy overwritten, duplicate ``#include "etoh.itp"`` lines,
``gmx grompp`` fatal "moleculetype redefined") shipped with every e2e green
(520ad042 commit message says this explicitly).

What is exercised (plan 48.3-14, G2 of RESEARCH-INVENTORY §4):

  1. Real sI hydrate with a CUSTOM cage guest from the UNRENAMED
     ``quickice/data/custom/etoh.gro``/``etoh.itp`` (``guest_residue_name="MOL"``
     → cage-guest ITP stages as ``etoh.itp`` with moleculetype ``MOL_H``).
  2. The SAME UNRENAMED etoh pair inserted as the LIQUID custom molecule via
     ``CustomMoleculeInserter`` — moleculetype ``etoh`` (D1 reconciliation,
     48.3-02).  NO renaming anywhere in this file (grep-asserted: zero
     occurrences of "cmet").
  3. Full downstream chain like the real GUI flow: custom → solute (source =
     "Custom Molecule") → ion (source = "Solute"), fresh interface per inserter.
  4. All 4 GUI exporters (interface / solute / custom-molecule / ion) with
     ``hydrate_config`` threaded and ``QFileDialog``/``QMessageBox`` patched
     (Pattern B, per tests/test_e2e_custom_guest_cross_tab_gui.py).

Collision-specific asserts (the UAT-F fix surface, ``quickice/gui/export.py``):

  - TWO distinct staged ITPs: the MOL_H-transformed cage-guest ``etoh.itp`` AND
    the collision-renamed liquid custom ITP.  The renamed basename is NOT
    guessed: it is derived from the production resolver
    ``_resolve_custom_molecule_itp_name`` itself (renames to ``{stem}_L{suffix}``
    on collision, mirroring the built-in _H/_L convention → ``etoh_L.itp``).
  - The staged ``etoh.itp`` still contains moleculetype ``MOL_H`` (the liquid
    copy did NOT overwrite the cage-guest copy).
  - The .top #includes BOTH files EXACTLY once each (raw-count grep-assert —
    ``parse_top_includes`` returns a list so duplicates are visible; the shipped
    bug produced a duplicate ``#include "etoh.itp"`` line).
  - ``.top [molecules]`` has ``MOL_H`` (cage) AND ``etoh`` (liquid custom);
    ``.gro`` residues match verbatim (D1 strict — option-a).
  - ``assert_itp_completeness`` + ``assert_gro_top_consistent`` STRICT
    (decision D1 = option-a; no fallback recipe).
  - ``gmx grompp`` rc == 0 — the authoritative "moleculetype etoh is redefined"
    class detector (@gmx_skipif so CI without gmx still runs the file checks).

Sensitivity self-check (plan Task 2.2): if ``_resolve_custom_molecule_itp_name``
were bypassed, the exporter would stage the liquid copy OVER ``etoh.itp``
(destroying the MOL_H moleculetype) and emit a DUPLICATE ``#include "etoh.itp"``
— this test fails at FOUR independent asserts (``etoh_L.itp`` missing, staged
``etoh.itp`` missing ``MOL_H``, duplicate-include count, grompp rc != 0).  The
asserted liquid ITP name (``etoh_L.itp``) is the RESOLVED name from the exporter
call path (export.py:261/447/621 → writer ``custom_molecule_itp_name`` kwarg →
``#include``), not the original ``etoh.itp``.

Plan: 48.3-14 (wave 4).  Depends on 48.3-01 (baselines/gates) and 48.3-02
(D1 decision + UAT-F collision fix landed in 44.1-13 lineage).
"""

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.conftest import gmx_skipif  # noqa: E402
from quickice.structure_generation.hydrate_generator import (  # noqa: E402
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab  # noqa: E402
from quickice.structure_generation.custom_molecule_inserter import (  # noqa: E402
    CustomMoleculeInserter,
)
from quickice.structure_generation.types import (  # noqa: E402
    CustomMoleculeConfig,
    HydrateConfig,
    InterfaceConfig,
)
from quickice.gui.export import (  # noqa: E402
    CustomMoleculeGROMACSExporter,
    InterfaceGROMACSExporter,
    IonGROMACSExporter,
    SoluteGROMACSExporter,
    _resolve_custom_molecule_itp_name,
)
from tests.e2e_export_helpers import (  # noqa: E402
    ETOH_GRO,
    ETOH_ITP,
    MDP_PATH,
    _insert_ions_from_solute,
    _insert_solutes,
    assert_gro_top_consistent,
    assert_itp_completeness,
    parse_gro_residue_names,
    parse_top_includes,
    parse_top_molecules,
    run_gmx_grompp,
)


# ── Shared custom-guest metadata (same etoh files for BOTH roles — the point) ─

_GUEST_TYPE = "etoh_e2e"
_GUEST_RESIDUE_NAME = "MOL"
_GUEST_ATOM_LABELS = ["H", "C", "H", "H", "C", "H", "H", "O", "H"]
_GUEST_ATOM_COUNT = 9

# The RESOLVED liquid custom ITP basename — derived from the PRODUCTION resolver
# (export.py:106), NOT guessed.  On a cage-guest basename collision the resolver
# renames the liquid copy to f"{stem}_L{suffix}".  Deriving it here (instead of
# hardcoding a guess) is the plan's sensitivity requirement: the name this test
# asserts is by construction the name the exporter call path produces.
_LIQUID_CM_ITP_NAME = _resolve_custom_molecule_itp_name(
    ETOH_ITP, {"etoh.itp": "/nonexistent/etoh.itp"}
)[0]


def _count_molecule_lines(top_path: str, molecule_name: str) -> int:
    """Count raw ``[ molecules ]`` lines starting with ``molecule_name``.

    ``parse_top_molecules`` returns a ``dict`` so duplicate keys collapse
    (last value wins).  Counting raw lines proves the .top has EXACTLY ONE
    entry per moleculetype — a duplicate ``MOL_H``/``etoh`` line would be the
    same "two streams both written" bug class as the duplicate #include.
    """
    count = 0
    in_molecules = False
    with open(top_path, "r") as f:
        for line in f:
            stripped = line.strip()
            if stripped.startswith("["):
                section = stripped.strip("[] \t").lower()
                in_molecules = (section == "molecules")
                continue
            if not in_molecules:
                continue
            if not stripped or stripped.startswith(";") or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if parts and parts[0] == molecule_name:
                count += 1
    return count


# ══════════════════════════════════════════════════════════════════════════════
# Module-scoped fixture: UNRENAMED etoh in BOTH roles + full downstream chain
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def collision_chain():
    """Build the same-basename-collision system ONCE per module.

    Amortizes the GenIce2 generation across the 4 parametrized export cases
    (AGENTS.md testing guidance).  A FRESH ``assemble_slab`` interface is
    derived per inserter (the ion inserter mutates ``iface.molecule_index``
    at ``ion_inserter.py:259``; each inserter gets its own unmutated copy —
    ``assemble_slab`` is deterministic with ``seed=42``).  All inserters
    return NEW structures (V-17 compliant).

    Chain shape mirrors the real GUI tab order (AGENTS.md cross-tab flow):
    hydrate(Tab 0/1) → interface(Tab 2) → custom(Tab 3) → solute(Tab 4,
    source="Custom Molecule") → ion(Tab 5, source="Solute").

    Returns a dict with keys:
        config -- HydrateConfig (custom cage guest: UNRENAMED etoh, MOL, 9 atoms)
        iface  -- InterfaceStructure (slab, 3x3x8 nm box >= 3.0 nm for PBC)
        custom -- CustomMoleculeStructure (1 UNRENAMED etoh liquid molecule)
        solute -- SoluteStructure (CH4 solutes; carries the custom molecule)
        ion    -- IonStructure (Na+/Cl-; carries solutes + the custom molecule)
    """
    # 1. Real sI hydrate with a CUSTOM cage guest from the UNRENAMED etoh files
    #    (44.1-21 same_custom_two_cages config shape).  The cage-guest ITP will
    #    stage as ``etoh.itp`` transformed to moleculetype ``MOL_H``.
    gen = HydrateStructureGenerator()
    config = HydrateConfig(
        lattice_type="sI",
        guest_type=_GUEST_TYPE,
        guest_residue_name=_GUEST_RESIDUE_NAME,
        guest_gro_path=str(ETOH_GRO),
        guest_itp_path=str(ETOH_ITP),
        guest_atom_labels=list(_GUEST_ATOM_LABELS),
        guest_atom_count=_GUEST_ATOM_COUNT,
        supercell_x=1,
        supercell_y=1,
        supercell_z=1,
    )
    hydrate = gen.generate(config)
    candidate = hydrate.to_candidate()

    # 2. Fresh slab interface per consumer.  Box 3x3x8 nm: shortest vector
    #    3.0 nm > 2 * cutoff (1.0 nm) for grompp's PBC rule (em.mdp).
    def _make_iface():
        return assemble_slab(
            candidate,
            InterfaceConfig(
                mode="slab",
                box_x=3.0,
                box_y=3.0,
                box_z=8.0,
                seed=42,
                ice_thickness=2.0,
                water_thickness=4.0,
            ),
        )

    iface = _make_iface()
    iface_custom = _make_iface()

    assert iface.guest_nmolecules > 0, "custom ethanol slab should have guests"
    assert iface.guest_atom_count == _GUEST_ATOM_COUNT * iface.guest_nmolecules, (
        f"slab guest_atom_count={iface.guest_atom_count} != "
        f"{_GUEST_ATOM_COUNT} * guest_nmolecules={iface.guest_nmolecules}"
    )

    # 3. The SAME UNRENAMED etoh pair as the LIQUID custom molecule.
    #    NO renaming anywhere — the collision IS the scenario (G2).  The D1
    #    reconciliation (48.3-02) registers the molecule under the ITP
    #    [moleculetype] name "etoh" (<=5 chars, usable as a GRO residue name).
    cm_config = CustomMoleculeConfig(
        placement_mode="random",
        gro_path=ETOH_GRO,
        itp_path=ETOH_ITP,
        molecule_count=1,
    )
    custom = CustomMoleculeInserter(cm_config, seed=42).place_random(iface_custom, 1)
    assert custom.custom_molecule_count == 1, (
        "custom molecule inserter should place 1 molecule in the water region"
    )
    assert custom.moleculetype_name == "etoh", (
        f"D1 reconciliation should register the liquid molecule under the ITP "
        f"[moleculetype] name 'etoh', got {custom.moleculetype_name!r}"
    )
    assert Path(custom.itp_path).name == "etoh.itp", (
        "liquid custom molecule must use the UNRENAMED etoh.itp (the collision "
        "IS the scenario — no cmet pre-renaming)"
    )
    assert custom.guest_atom_count > 0, (
        "CustomMoleculeStructure.guest_atom_count must be propagated from the "
        "interface for the staging helper's presence gate"
    )

    # 4. Solute: source = the custom structure (GUI Solute tab, source
    #    "Custom Molecule" — main_window.py:1161 passes the full
    #    CustomMoleculeStructure so solute_inserter preserves custom data).
    solute = _insert_solutes(custom, solute_type="CH4", concentration=0.3)
    assert solute.n_molecules > 0, "solute inserter should place CH4 molecules"
    assert solute.custom_molecule_count == 1, (
        "SoluteStructure must carry the custom molecule through the chain"
    )
    assert Path(solute.custom_itp_path).name == "etoh.itp", (
        "SoluteStructure.custom_itp_path must stay the UNRENAMED etoh.itp"
    )

    # 5. Ion: source = the solute (GUI Ion tab, source "Solute" —
    #    main_window.py:930-955 uses solute_structure.interface_structure with
    #    solute + custom attrs stashed; _insert_ions_from_solute replicates
    #    that hand-off).  This is the FULL downstream chain: the ion export
    #    must carry cage guests + liquid custom + solutes + ions together —
    #    the exact tab export class where UAT Issue 2 failed.
    ion = _insert_ions_from_solute(solute, concentration=0.15)
    assert (ion.na_count > 0 or ion.cl_count > 0), (
        "ion inserter should place Na+ / Cl- ions"
    )
    assert ion.custom_molecule_count == 1, (
        "IonStructure must carry the custom molecule through the chain"
    )
    assert Path(ion.custom_itp_path).name == "etoh.itp", (
        "IonStructure.custom_itp_path must stay the UNRENAMED etoh.itp"
    )
    assert ion.solute_n_molecules > 0, (
        "IonStructure must carry the solutes through the chain"
    )
    assert ion.guest_nmolecules > 0, (
        "IonStructure.guest_nmolecules must be propagated from the interface"
    )

    return {
        "config": config,
        "iface": iface,
        "custom": custom,
        "solute": solute,
        "ion": ion,
    }


