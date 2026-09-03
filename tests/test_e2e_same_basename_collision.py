"""G2 regression: SAME-basename collision — etoh as BOTH cage guest AND liquid custom molecule.

NO pre-renaming to a collision-free copy — the collision IS the scenario.  This
is the exact real-user input (UAT Issue 2 / P2 fixture-sanitization class): the
user uploads the SAME ``etoh.gro``/``etoh.itp`` pair as the hydrate cage guest
(Tab 1) AND as the liquid custom molecule (Tab 3).  The three pre-existing
cross-tab e2e tests deliberately renamed the liquid copy to a collision-free
basename "to avoid the etoh.itp filename collision" — the fixture pre-solved the
exact UX scenario that bites real users, which is why the duplicate-#include bug
(both ITPs staged as ``etoh.itp``, the cage-guest MOL_H copy overwritten,
duplicate ``#include "etoh.itp"`` lines, ``gmx grompp`` fatal "moleculetype
redefined") shipped with every e2e green (520ad042 commit message says this
explicitly).  This file is grep-gated to ZERO occurrences of that legacy rename
token (the plan's verification gate).

What is exercised (plan 48.3-14, G2 of RESEARCH-INVENTORY §4):

  1. Real sI hydrate with a CUSTOM cage guest from the UNRENAMED
     ``quickice/data/custom/etoh.gro``/``etoh.itp`` (``guest_residue_name="MOL"``
     → cage-guest ITP stages as ``etoh.itp`` with moleculetype ``MOL_H``).
  2. The SAME UNRENAMED etoh pair inserted as the LIQUID custom molecule via
     ``CustomMoleculeInserter`` — moleculetype ``etoh`` (D1 reconciliation,
     48.3-02).  NO renaming anywhere in this file (grep-gated: zero
     occurrences of the legacy pre-rename token).
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
        "IS the scenario — no pre-renaming to a collision-free copy)"
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


# ══════════════════════════════════════════════════════════════════════════════
# Parametrized 4-exporter grompp test + collision-specific asserts
# ══════════════════════════════════════════════════════════════════════════════

# Each case: (exporter_id, exporter_class, structure_key, expected_molecules,
#             collision_expected, extra_expected_itps)
# - expected_molecules: subset that MUST appear in .top [molecules] + .gro
#   residues (ion NA/CL asserted conditionally, cross-tab precedent).
# - collision_expected: True when the export carries BOTH the cage guest AND
#   the liquid custom molecule (solute / custom-molecule / ion exports).
#   The interface export has NO liquid custom molecule (Tab 2 precedes Tab 3),
#   so exactly ONE guest ITP (etoh.itp, MOL_H) is staged there and the
#   collision-rename machinery must NOT fire.
# - extra_expected_itps: ITPs beyond the always-present tip4p-ice.itp +
#   etoh.itp (MOL_H cage guest).
_EXPORT_CASES = [
    pytest.param(
        "interface",
        InterfaceGROMACSExporter,
        "iface",
        {"SOL", "MOL_H"},
        False,
        (),
        id="interface",
    ),
    pytest.param(
        "solute",
        SoluteGROMACSExporter,
        "solute",
        {"SOL", "MOL_H", "etoh", "CH4_L"},
        True,
        ("ch4_liquid.itp",),
        id="solute",
    ),
    pytest.param(
        "custom_molecule",
        CustomMoleculeGROMACSExporter,
        "custom",
        {"SOL", "MOL_H", "etoh"},
        True,
        (),
        id="custom_molecule",
    ),
    pytest.param(
        "ion",
        IonGROMACSExporter,
        "ion",
        {"SOL", "MOL_H", "etoh", "CH4_L"},  # NA / CL asserted conditionally
        True,
        ("ion.itp", "ch4_liquid.itp"),
        id="ion",
    ),
]


@gmx_skipif
@pytest.mark.parametrize(
    "exporter_id,exporter_class,structure_key,expected_molecules,"
    "collision_expected,extra_expected_itps",
    _EXPORT_CASES,
)
def test_same_basename_collision_gui_full_chain_grompp(
    collision_chain,
    tmp_path,
    exporter_id,
    exporter_class,
    structure_key,
    expected_molecules,
    collision_expected,
    extra_expected_itps,
):
    """The SAME etoh files as cage guest + liquid custom molecule export
    grompp-clean through EACH of the 4 GUI exporters.

    The core G2 assertion: the cage-guest ITP stages as ``etoh.itp``
    (moleculetype ``MOL_H``) and the liquid custom ITP stages under its
    RESOLVED collision name ``etoh_L.itp`` (moleculetype ``etoh``) — TWO
    distinct files, TWO distinct moleculetypes, each ``#include``d EXACTLY
    once, and ``gmx grompp`` exits 0 (no "moleculetype redefined", no
    duplicate-include fatal).

    Flow (each parametrized case):
      1. ``exporter = {ExporterClass}(parent_widget=None)``.
      2. Patch ``quickice.gui.export.QFileDialog.getSaveFileName`` + the whole
         ``quickice.gui.export.QMessageBox`` class (Pattern B — under
         ``QT_QPA_PLATFORM=offscreen`` an unpatched getSaveFileName returns
         ``("", "")`` and the export silently writes nothing).
      3. ``exporter.export_*_gromacs(structure, hydrate_config=config)`` —
         the exporter stages the cage-guest ITP via
         ``_stage_hydrate_guest_itps`` (transformed, moleculetype ``MOL_H``)
         and resolves the liquid custom ITP name via
         ``_resolve_custom_molecule_itp_name`` (UAT-F fix).
      4. Collision asserts (solute / custom-molecule / ion cases):
         ``etoh_L.itp`` staged, staged ``etoh.itp`` still ``MOL_H``, .top
         #includes BOTH exactly once each, ``[molecules]`` has ``MOL_H`` +
         ``etoh`` with raw-line counts of exactly 1 each.
      5. ``assert_itp_completeness`` + ``assert_gro_top_consistent`` STRICT
         (D1 = option-a — no fallback recipe).
      6. ``gmx grompp`` rc == 0.
    """
    config = collision_chain["config"]
    structure = collision_chain[structure_key]

    # The resolved liquid ITP name must be the collision-renamed basename —
    # derived from the production resolver at import time (sensitivity
    # self-check: this pins the rename convention; if the resolver changed,
    # THIS assert flips before any stale-name false-pass).
    assert _LIQUID_CM_ITP_NAME == "etoh_L.itp", (
        f"production _resolve_custom_molecule_itp_name returned "
        f"{_LIQUID_CM_ITP_NAME!r} for the etoh collision — the rename "
        f"convention changed; update this test's expected name (do NOT keep "
        f"asserting a stale name)"
    )

    # 1-2. Pattern B: mock QFileDialog + QMessageBox so the exporter runs
    #      end-to-end headless.  getSaveFileName is called ONCE (.top derived
    #      from the .gro stem) — matches 44.1-19 / 48.3-13 precedent.
    gro_path = tmp_path / "output.gro"
    top_path = tmp_path / "output.top"
    with patch(
        "quickice.gui.export.QFileDialog.getSaveFileName",
        return_value=(str(gro_path), "GRO Files (*.gro)"),
    ), patch("quickice.gui.export.QMessageBox"):
        exporter = exporter_class(parent_widget=None)
        if exporter_id == "interface":
            ok = exporter.export_interface_gromacs(
                structure, hydrate_config=config
            )
        elif exporter_id == "solute":
            ok = exporter.export_solute_gromacs(
                structure, hydrate_config=config
            )
        elif exporter_id == "custom_molecule":
            ok = exporter.export_custom_molecule_gromacs(
                structure, hydrate_config=config
            )
        elif exporter_id == "ion":
            ok = exporter.export_ion_gromacs(
                structure, hydrate_config=config
            )
        else:  # pragma: no cover - exhaustive dispatcher
            raise AssertionError(f"unknown exporter_id: {exporter_id}")
        assert ok is True, (
            f"[{exporter_id}] export returned False — export failed (QFileDialog "
            f"mock may not have been picked up, or staging raised; the UAT-F "
            f"collision path is exercised here)"
        )

    # 3. Files written by the exporter.
    assert gro_path.exists(), f"[{exporter_id}] .gro not written: {gro_path}"
    assert top_path.exists(), f"[{exporter_id}] .top not written: {top_path}"
    assert (tmp_path / "tip4p-ice.itp").exists(), (
        f"[{exporter_id}] water ITP (tip4p-ice.itp) not staged by the exporter"
    )

    # ── Collision-specific asserts ───────────────────────────────────────────
    # The cage-guest ITP stages as etoh.itp (MOL_H-transformed) in ALL cases.
    staged_guest = tmp_path / "etoh.itp"
    assert staged_guest.exists(), (
        f"[{exporter_id}] cage-guest ITP (etoh.itp) not staged by "
        f"_stage_hydrate_guest_itps"
    )
    staged_guest_text = staged_guest.read_text()
    assert "MOL_H" in staged_guest_text, (
        f"[{exporter_id}] staged etoh.itp is missing the MOL_H moleculetype — "
        f"transform_guest_itp was not applied (or the liquid custom copy "
        f"OVERWROTE the cage-guest ITP — the pre-UAT-F bug)"
    )

    if collision_expected:
        # TWO DISTINCT staged ITPs: the collision-renamed liquid custom ITP
        # must exist BESIDE (not instead of) the cage-guest ITP.  The name is
        # the RESOLVED name from the production resolver, not the original
        # etoh.itp — if _resolve_custom_molecule_itp_name were bypassed, this
        # file would not exist and the liquid copy would have clobbered
        # etoh.itp above.
        staged_liquid = tmp_path / _LIQUID_CM_ITP_NAME
        assert staged_liquid.exists(), (
            f"[{exporter_id}] collision-renamed liquid custom ITP "
            f"({_LIQUID_CM_ITP_NAME}) not staged — _resolve_custom_molecule_itp_name "
            f"was bypassed or the exporter staged the liquid copy under the "
            f"cage-guest basename (the pre-UAT-F duplicate-#include bug)"
        )
        # The liquid copy must be the raw-moleculetype copy (moleculetype
        # "etoh"), NOT a second MOL_H transform — two distinct moleculetypes
        # is what makes the pair grompp-valid.
        staged_liquid_text = staged_liquid.read_text()
        assert "MOL_H" not in staged_liquid_text, (
            f"[{exporter_id}] staged {_LIQUID_CM_ITP_NAME} must be the "
            f"liquid moleculetype copy (etoh), not a second _H transform"
        )

    includes = parse_top_includes(str(top_path))

    # NO duplicate #include lines at all — THE shipped-bug detector (the old
    # bug emitted '#include "etoh.itp"' twice: once for the cage guest, once
    # for the liquid custom molecule).
    dupes = {name for name in includes if includes.count(name) > 1}
    assert not dupes, (
        f"[{exporter_id}] .top has DUPLICATE #include lines: {sorted(dupes)} "
        f"(all includes: {includes}) — the UAT Issue 2 duplicate-include bug "
        f"class"
    )

    if collision_expected:
        # .top #includes BOTH files, each EXACTLY once.
        assert includes.count("etoh.itp") == 1, (
            f"[{exporter_id}] .top must #include the cage-guest etoh.itp "
            f"EXACTLY once, got {includes.count('etoh.itp')} in {includes}"
        )
        assert includes.count(_LIQUID_CM_ITP_NAME) == 1, (
            f"[{exporter_id}] .top must #include the RESOLVED liquid custom "
            f"ITP '{_LIQUID_CM_ITP_NAME}' EXACTLY once "
            f"(got {includes.count(_LIQUID_CM_ITP_NAME)} in {includes}) — a "
            f"count of 0 means the collision rename was bypassed; a count of "
            f"2 means a duplicate include"
        )
    else:
        # Interface export: NO liquid custom molecule exists yet (Tab 2
        # precedes Tab 3) — the collision-rename machinery must NOT fire and
        # no liquid ITP may be staged or referenced.
        assert _LIQUID_CM_ITP_NAME not in includes, (
            f"[{exporter_id}] interface export must not reference the liquid "
            f"custom ITP {_LIQUID_CM_ITP_NAME} (no liquid custom molecule in "
            f"an interface-only export), got {includes}"
        )
        assert not (tmp_path / _LIQUID_CM_ITP_NAME).exists(), (
            f"[{exporter_id}] interface export must not stage "
            f"{_LIQUID_CM_ITP_NAME}"
        )

    # 4. Stage the MDP + run the file-consistency gates.  D1 = option-a:
    #    assert_gro_top_consistent STRICT (no fallback recipe) — every
    #    [molecules] name must appear as a .gro residue verbatim (the liquid
    #    custom molecule matches 'etoh' in both files after the 48.3-02 D1
    #    reconciliation).
    shutil.copy(MDP_PATH, tmp_path / "em.mdp")
    assert_itp_completeness(str(top_path), tmp_path)
    assert_gro_top_consistent(str(gro_path), str(top_path))

    # 5. gmx grompp — the authoritative "moleculetype etoh is redefined" /
    #    "No such moleculetype" class detector.  Must exit 0.
    exit_code, stderr = run_gmx_grompp(
        tmp_path, gro_file="output.gro", top_file="output.top"
    )
    assert exit_code == 0, (
        f"[{exporter_id}] gmx grompp failed (same-basename collision, "
        f"{exporter_class.__name__}):\n{stderr}"
    )

    # 6. .top [molecules] + .gro residues: the cage stream (MOL_H) AND the
    #    liquid stream (etoh) must BOTH survive into the export — neither may
    #    be eaten by the other.  GUE must never appear (custom_guest_info not
    #    threaded).
    mols = parse_top_molecules(str(top_path))
    for mol in expected_molecules:
        assert mol in mols, (
            f"[{exporter_id}] expected '{mol}' in [molecules], got {mols}"
        )
    assert "GUE" not in mols, (
        f"[{exporter_id}] GUE must NOT appear in [molecules] "
        f"(custom_guest_info not threaded): {mols}"
    )

    # Count parity per stream (guards "one stream ate the other"):
    # - MOL_H count == the structure's propagated cage-guest molecule count.
    # - etoh count == the liquid custom molecule count (1) — only in the
    #   collision cases.
    guest_counts = {
        "iface": collision_chain["iface"].guest_nmolecules,
        "solute": collision_chain["solute"].interface_structure.guest_nmolecules,
        "custom": collision_chain["custom"].guest_nmolecules,
        "ion": collision_chain["ion"].guest_nmolecules,
    }
    assert mols["MOL_H"] == guest_counts[structure_key], (
        f"[{exporter_id}] MOL_H count {mols['MOL_H']} != propagated cage-guest "
        f"count {guest_counts[structure_key]} — the cage-guest stream was "
        f"corrupted by the collision handling"
    )
    if collision_expected:
        assert mols["etoh"] == 1, (
            f"[{exporter_id}] liquid custom 'etoh' count {mols['etoh']} != 1 "
            f"— the liquid custom stream was corrupted by the collision handling"
        )
    else:
        assert "etoh" not in mols, (
            f"[{exporter_id}] interface export must not list the liquid custom "
            f"moleculetype 'etoh' in [molecules], got {mols}"
        )

    # Raw-line counts: EXACTLY ONE [molecules] line per stream (parse_top_molecules
    # is a dict and would hide duplicates; the raw count cannot).
    mol_h_lines = _count_molecule_lines(str(top_path), "MOL_H")
    assert mol_h_lines == 1, (
        f"[{exporter_id}] expected EXACTLY ONE MOL_H line in [molecules], "
        f"got {mol_h_lines}"
    )
    if collision_expected:
        etoh_lines = _count_molecule_lines(str(top_path), "etoh")
        assert etoh_lines == 1, (
            f"[{exporter_id}] expected EXACTLY ONE liquid 'etoh' line in "
            f"[molecules], got {etoh_lines}"
        )

    # Ion case: NA / CL asserted conditionally (only when ions were placed) —
    # cross-tab precedent (test_e2e_custom_guest_cross_tab_gui.py:402-412).
    if exporter_id == "ion":
        ion_struct = collision_chain["ion"]
        if ion_struct.na_count > 0:
            assert "NA" in mols, (
                f"[ion] expected NA in [molecules] (na_count>0), got {mols}"
            )
        if ion_struct.cl_count > 0:
            assert "CL" in mols, (
                f"[ion] expected CL in [molecules] (cl_count>0), got {mols}"
            )

    # .gro residues must match the .top streams (D1: verbatim 'etoh'; the
    # cage guest is 'MOL_H', never bare 'MOL').
    gro_res = set(parse_gro_residue_names(str(gro_path)))
    for mol in expected_molecules:
        assert mol in gro_res, (
            f"[{exporter_id}] expected '{mol}' in .gro residues, got {gro_res}"
        )
    assert "GUE" not in gro_res, (
        f"[{exporter_id}] GUE must NOT appear in .gro residues "
        f"(custom_guest_info not threaded): {gro_res}"
    )
    if exporter_id == "ion":
        ion_struct = collision_chain["ion"]
        if ion_struct.na_count > 0:
            assert "NA" in gro_res, (
                f"[ion] expected NA in .gro residues (na_count>0), got {gro_res}"
            )
        if ion_struct.cl_count > 0:
            assert "CL" in gro_res, (
                f"[ion] expected CL in .gro residues (cl_count>0), got {gro_res}"
            )
