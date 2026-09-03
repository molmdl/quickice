"""Shared module-scoped chain fixtures for the lattice e2e grompp suites.

48.3-20 fixture dedup (RESEARCH-INFRA §2.3): the 3 near-copy sibling fixture
clusters (measured similarity 0.85-0.90) were LINE-DIFFED at execution time
and their executable bodies verified IDENTICAL — the only differences were
docstring wording, comment arrangement, and assert-message text (plus one
extra sanity assert in the GUI copy of ``filled_ice_hydrates``, kept here as
a strict superset that holds for both consumers). They are extracted into
this ONE plain module — NOT a conftest (the INFRA collision rule forbids new
conftest files in the e2e tree). Fixtures imported into a test module's
namespace are resolved by pytest normally and keep their declared module
scope (one instantiation per consuming module, exactly as when each file
owned its own def).

Consumers (extracted clusters; paths post-48.3-21..24 e2e regrouping —
pre-regroup root-level locations remain git-history traceable):
- ``custom_guest_chains`` <- tests/e2e/custom_guest/test_e2e_custom_guest_lattices_cli.py (48.3-11)
                           + tests/e2e/custom_guest/test_e2e_custom_guest_lattices_gui.py (48.3-10)
- ``lattice_chains``      <- tests/e2e/interface/test_e2e_lattice_interface_cli.py (45-02)
                           + tests/e2e/interface/test_e2e_lattice_interface_gui.py (45-01)
- ``filled_ice_hydrates`` <- tests/e2e/hydrate/test_e2e_filled_ice_cli_hydrate_grompp.py (47-05)
                           + tests/e2e/lattice/test_e2e_mixed_filled_ice_gui.py (45-14)

Divergent same-name sibling fixtures (measured similarity 0.04-0.31:
``cross_tab_lattice_chains_cli/_gui``, ``blocking_triclinic_hydrates`` /
``triclinic_hydrate_exports``, ``sH_cross_tab_chain``) are NOT here — they
were RENAMED apart in their own files, never merged (48.2 warning: merging
subtly different fixtures that happen to share a name silently changes
behavior).

GenIce2 amortization (AGENTS.md): each fixture is module-scoped so the slow
hydrate generation + slab assembly runs once per lattice per consuming test
module.
"""

import shutil
from types import SimpleNamespace

import pytest

from quickice.structure_generation.hydrate_generator import (
    HydrateStructureGenerator,
)
from quickice.structure_generation.modes.slab import assemble_slab
from quickice.structure_generation.custom_molecule_inserter import (
    CustomMoleculeInserter,
)
from quickice.structure_generation.types import (
    CageGuestAssignment,
    CustomMoleculeConfig,
    HYDRATE_LATTICES,
    HydrateConfig,
    InterfaceConfig,
)
from tests.e2e_export_helpers import (
    ETOH_GRO,
    ETOH_ITP,
    _insert_ions_from_solute,
    _insert_solutes,
)


# -- Canonical lattice sets (single source of truth for fixtures AND the
#    consumers' parametrize decorators — one definition, imported by both) ----

# The 4 non-sI lattices that support custom guests (have cages). sTprime/17
# are water-only (no cages -> custom guest is N/A); c0te/c1te are triclinic
# BLOCKED at the interface tab (see 45-08/45-09 for hydrate-only export); sH
# is triclinic-but-allowed and also supports custom guests (covered
# separately — huge guest count, Pitfall 5).
CUSTOM_GUEST_LATTICES = ("sII", "c2te", "ice1hte", "16")

# Lattices WITH cage guests (built-in ch4). Water-only lattices ignore the
# guest_type="ch4" in the generator (the water-only skip in
# hydrate_generator.py drops cages entirely), so the resulting hydrate has
# guest_nmolecules == 0.
INTERFACE_LATTICES_WITH_GUESTS = frozenset(("sII", "c2te", "ice1hte", "16"))
INTERFACE_LATTICES_WATER_ONLY = frozenset(("sTprime", "17"))
INTERFACE_LATTICES = ("sII", "c2te", "ice1hte", "sTprime", "16", "17")

# Per-lattice supercell sizes for the filled-ice lattices (Pitfall 1 —
# empirically verified minimums): c2te 1x1x1 shortest = 0.88 nm,
# 2x2x2 = 1.76 nm, 3x3x3 = 2.65 nm (PASSES). ice1hte 1x1x1 shortest =
# 0.69 nm, 2x2x2 = 1.38 nm, 3x3x3 = 2.07 nm (FAILS — GROMACS's check is
# stricter than the simple vector-length test for non-orthogonal cells),
# 4x4x4 = 2.76 nm (PASSES). Using per-lattice minimums minimizes atom count
# while ensuring grompp rc=0.
FILLED_ICE_SUPERCELLS = {
    "c2te": (3, 3, 3),
    "ice1hte": (4, 4, 4),
}


# ══════════════════════════════════════════════════════════════════════════════
# custom_guest_chains — extracted from 48.3-10 (GUI) + 48.3-11 (CLI)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def custom_guest_chains(tmp_path_factory):
    """Build the custom-ethanol-guest hydrate + slab interfaces + the 3
    downstream inserter structures ONCE per lattice.

    Amortizes the GenIce2 generation (``HydrateStructureGenerator.generate``)
    across the 4 interface + 12 downstream parametrized export cases (per
    AGENTS.md testing guidance — GenIce2 is ~3-5s per lattice).  Each lattice
    builds an independent ``HydrateConfig`` (same custom ethanol guest,
    different ``lattice_type``) -> gen -> candidate -> ``assemble_slab``.

    48.3-10/48.3-11 (44.1-19 discipline, generate-once-derive-many): the
    candidate is generated ONCE per lattice, then a FRESH ``assemble_slab``
    interface is derived PER inserter (``seed=42`` -> deterministic identical
    slabs).  The ion inserter mutates ``iface.molecule_index`` when it is
    empty (real GenIce2 data, ``ion_inserter.py:259`` —
    ``structure.molecule_index = mol_index``), so each inserter gets its own
    interface to avoid cross-contaminating the interface exporter's
    reference.  The ion chain follows the REAL cross-tab data flow
    (Tab 3 -> Tab 4, CP-01): ``_insert_ions_from_solute`` operates on
    ``solute.interface_structure`` (duck-typed solute attributes attached);
    the resulting molecule_index mutation is contained to the
    solute-dedicated interface and is the DESIGNED-FOR scenario in
    ``write_solute_gro_file`` (per-molecule ``mol_type`` guest resolution,
    solute_writer.py "Issue 3" comment block).

    All inserters return NEW structures (V-17 compliant).

    Box 3x3x8 nm: shortest vector 3.0 nm > 2 * cutoff (1.0 nm) for the grompp
    PBC rule (``rcoulomb=rvdw=1.0`` nm in ``em.mdp``). Deterministic
    (``seed=42``).

    MIRRORS the 44.1-20 template's custom ethanol config (lines 95-106),
    swapping ``lattice_type``. Use ETOH_GRO/ETOH_ITP absolute paths from
    e2e_export_helpers (CWD-independent). ``guest_residue_name="MOL"`` (3 chars)
    so the _H suffix yields ``"MOL_H"`` (5 chars, passes the GRO fixed-width
    limit).

    The liquid custom molecule uses a RENAMED COPY (cmet.gro/cmet.itp,
    moleculetype "MOL") to avoid the etoh.itp filename collision between the
    cage guest (staged as MOL_H via etoh.itp) and the custom molecule (copied
    with atomtypes commented).  Same workaround as plans 44.1-13 / 48.3-10.
    The cmet rename is intentional HERE; the SAME-basename (etoh.itp vs
    etoh.itp) collision scenario is plan 48.3-14's job, do not conflate.  The
    renamed copy lives in a module-scoped temp dir (the inserter needs the
    files to exist at fixture-setup time; function-scoped tmp_path is not yet
    available) and is shared across lattices (content is lattice-independent;
    staging/export copies into each case's own workspace without mutating
    the source).

    Returns a dict keyed by ``lattice_type`` ->
    ``SimpleNamespace(hydrate=hydrate, iface=iface, config=config,
    solute=solute, custom=custom, ion=ion)``.  The ``hydrate`` carries
    ``.config`` (the custom HydrateConfig) so BOTH consumers can read it —
    the GUI exporter and the CLI ``_run_export_step`` via
    ``self._hydrate_result.config`` to build ``custom_guest_info``.
    """
    # Renamed custom-molecule copy (cmet.gro/cmet.itp, moleculetype "MOL") —
    # avoids the etoh.itp basename collision with the cage-guest staging.
    cm_dir = tmp_path_factory.mktemp("custom_molecule_data")
    cmet_gro = cm_dir / "cmet.gro"
    cmet_itp = cm_dir / "cmet.itp"
    shutil.copy(ETOH_GRO, cmet_gro)
    cmet_lines = ETOH_ITP.read_text().splitlines(keepends=True)
    _in_moltype = False
    for i, line in enumerate(cmet_lines):
        if "[ moleculetype ]" in line:
            _in_moltype = True
        elif _in_moltype and line.strip() and not line.strip().startswith(";"):
            # First non-comment, non-empty line after [ moleculetype ] is the
            # moleculetype name ("etoh       3"); rename "etoh" -> "MOL".
            cmet_lines[i] = line.replace("etoh", "MOL", 1)
            break
    cmet_itp.write_text("".join(cmet_lines))

    chains = {}
    for lattice_type in CUSTOM_GUEST_LATTICES:
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="etoh_e2e",
            guest_residue_name="MOL",
            guest_gro_path=str(ETOH_GRO),
            guest_itp_path=str(ETOH_ITP),
            guest_atom_labels=["H", "C", "H", "H", "C", "H", "H", "O", "H"],
            guest_atom_count=9,
            supercell_x=1,
            supercell_y=1,
            supercell_z=1,
        )
        hydrate = gen.generate(config)
        candidate = hydrate.to_candidate()

        # Fresh slab interface PER inserter from the shared candidate
        # (generate-once-derive-many, seed=42 -> deterministic identical).
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

        iface = _make_iface()  # interface exporter (never mutated)
        iface_solute = _make_iface()  # solute inserter + ion chain
        iface_custom = _make_iface()  # custom molecule inserter

        # Custom ethanol placed in cages (count varies by lattice — do NOT
        # assert exact counts, only > 0 + 9 * nmolecules consistency, the
        # 44.1-05 fix threading guest_atom_count through the slab detector).
        assert iface.guest_nmolecules > 0, (
            f"[{lattice_type}] custom ethanol slab should have guests"
        )
        assert iface.guest_atom_count == 9 * iface.guest_nmolecules, (
            f"[{lattice_type}] guest_atom_count={iface.guest_atom_count} != "
            f"9 * guest_nmolecules={9 * iface.guest_nmolecules}"
        )

        # SoluteStructure: CH4 solutes placed in the water region.
        # SoluteInserter creates its own registry internally; it does NOT
        # mutate the source interface (only reads via getattr).
        solute = _insert_solutes(
            iface_solute, solute_type="CH4", concentration=0.3
        )
        assert solute.n_molecules > 0, (
            f"[{lattice_type}] solute inserter should place CH4 molecules"
        )
        assert solute.interface_structure is not None, (
            f"[{lattice_type}] SoluteStructure.interface_structure must be "
            f"populated for staging + ion chaining"
        )

        # CustomMoleculeStructure: 1 cmet (renamed etoh) molecule in the
        # water region. After 48.3-02 D1 the inserter registers the ITP
        # moleculetype name ("MOL", <=5 chars) so .gro residues + .top
        # [molecules] agree strictly.
        cm_config = CustomMoleculeConfig(
            placement_mode="random",
            gro_path=cmet_gro,
            itp_path=cmet_itp,
            molecule_count=1,
        )
        inserter = CustomMoleculeInserter(cm_config, seed=42)
        custom = inserter.place_random(iface_custom, 1)
        assert custom.custom_molecule_count > 0, (
            f"[{lattice_type}] custom molecule inserter should place 1 "
            f"molecule in the water region"
        )
        assert custom.guest_atom_count > 0, (
            f"[{lattice_type}] CustomMoleculeStructure.guest_atom_count must "
            f"be propagated from the interface for the custom-guest staging "
            f"gate"
        )

        # IonStructure: Na+ / Cl- in the water region, built from the SOLUTE
        # (real cross-tab flow Tab 3 -> Tab 4 via _solute_to_ion_source /
        # BUG I5 workaround).  NOTE: replace_water_with_ions mutates
        # iface_solute.molecule_index (ion_inserter.py:259) when the
        # interface has no molecule_index (real GenIce2 data) — contained to
        # the solute-dedicated interface (see fixture docstring).
        ion = _insert_ions_from_solute(solute, concentration=0.15)
        assert (ion.na_count > 0 or ion.cl_count > 0), (
            f"[{lattice_type}] ion inserter should place Na+ / Cl- ions"
        )
        assert ion.guest_atom_count > 0, (
            f"[{lattice_type}] IonStructure.guest_atom_count must be "
            f"propagated from the interface for the custom-guest staging "
            f"block"
        )
        assert ion.guest_nmolecules > 0, (
            f"[{lattice_type}] IonStructure.guest_nmolecules must be "
            f"propagated from the interface for the custom-guest staging "
            f"block"
        )

        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate, iface=iface, config=config,
            solute=solute, custom=custom, ion=ion,
        )
    yield chains


# ══════════════════════════════════════════════════════════════════════════════
# lattice_chains — extracted from 45-01 (GUI) + 45-02 (CLI)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def lattice_chains():
    """Module-scoped: build the hydrate -> interface chain for EACH of the 6
    non-blocked new lattice types ONCE, amortizing the GenIce2 + assemble_slab
    calls (~1-5s each) across all parametrized export cases.

    For water-only lattices (sTprime, 17) ``guest_type="ch4"`` is ignored by
    the generator (the water-only skip drops cages), so the resulting hydrate
    has ``guest_nmolecules == 0``.

    Returns ``dict {lattice_type: SimpleNamespace}`` where each namespace
    carries ``hydrate`` (with ``.config``), ``iface`` (the assembled slab
    interface), and ``config`` (the ``HydrateConfig`` used). The chain MUST
    carry the hydrate (with ``.config``) -- NOT just the interface: the CLI
    ``_run_export_step`` reads ``hydrate_config = getattr(
    self._hydrate_result, "config", None)`` and the GUI exporter needs the
    config for the built-in guest staging path.
    """
    chains = {}
    for lattice_type in INTERFACE_LATTICES:
        gen = HydrateStructureGenerator()
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",
            supercell_x=1,
            supercell_y=1,
            supercell_z=1,
        )
        hydrate = gen.generate(config)
        candidate = hydrate.to_candidate()
        iface = assemble_slab(
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
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate,
            iface=iface,
            config=config,
        )
    yield chains


# ══════════════════════════════════════════════════════════════════════════════
# filled_ice_hydrates — extracted from 47-05 (CLI) + 45-14 (GUI)
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="module")
def filled_ice_hydrates():
    """Module-scoped: generate c2te + ice1hte hydrate structures with built-in
    CH4 in the single "small" cage ONCE, amortizing the GenIce2 calls across
    the parametrized CLI hydrate-branch + GUI exporter export cases.

    CRITICAL (Pitfall 2 — cage key): c2te/ice1hte have
    ``cage_type_map = {"small": "Ne1"}`` — a SINGLE key. The ``cages`` display
    dict uses the human-readable key "guest" (the cage NAME), but
    ``cage_type_map`` (the GenIce2 cage ID mapping used for guest placement
    via ``parse_guest``) uses "small". The ``cage_guest_assignments`` dict
    MUST use "small" as the key (matching ``cage_type_map``) — using "guest"
    produces 0 guests because the hydrate generator's ``_run_via_api``
    skips cage keys not present in ``cage_type_map`` (warning:
    "cage_key 'guest' not in cage_type_map").

    Per-lattice supercell sizes (Pitfall 1 — empirically verified):
      - c2te 3x3x3: shortest = 2.65 nm > 2.0 nm -> grompp rc=0 (7776 atoms)
      - ice1hte 4x4x4: shortest = 2.76 nm > 2.0 nm -> grompp rc=0 (6656 atoms)
    The plan's suggested 2x2x2 fails for BOTH (c2te=1.76 nm, ice1hte=1.38 nm —
    both < 2.0 nm); ice1hte even fails at 3x3x3 (2.07 nm) due to GROMACS's
    stricter non-orthogonal cell check.

    Returns ``dict {"c2te": SimpleNamespace(hydrate=..., config=...),
    "ice1hte": SimpleNamespace(hydrate=..., config=...)}`` where each
    namespace carries the ``HydrateStructure`` + the ``HydrateConfig`` used
    to generate it (the CLI hydrate branch reads ``hydrate.config`` for ITP
    staging via ``copy_itp_files_for_structure``; the GUI exporter needs
    both).
    """
    chains = {}
    for lattice_type in ("c2te", "ice1hte"):
        gen = HydrateStructureGenerator()
        nx, ny, nz = FILLED_ICE_SUPERCELLS[lattice_type]
        config = HydrateConfig(
            lattice_type=lattice_type,
            guest_type="ch4",  # primary (legacy) — ch4 is built-in
            cage_guest_assignments={
                # "small" matches cage_type_map key (NOT "guest" — the cages
                # display dict uses "guest", but cage_type_map uses "small").
                "small": CageGuestAssignment(
                    guest_type="ch4", occupancy=100.0
                ),
            },
            supercell_x=nx,  # Pitfall 1: per-lattice minimum supercell.
            supercell_y=ny,
            supercell_z=nz,
        )
        hydrate = gen.generate(config)
        # Sanity: filled-ice single cage should place CH4 guests.
        assert hydrate.guest_count > 0, (
            f"{lattice_type} filled-ice should have cage guests, "
            f"got guest_count={hydrate.guest_count} (check cage key — "
            f"cage_type_map={HYDRATE_LATTICES[lattice_type]['cage_type_map']})"
        )
        # Superset sanity (from the 45-14 GUI copy; holds for the CLI
        # consumer too — the same ch4-filled hydrates are built).
        mol_types = {m.mol_type for m in hydrate.molecule_index}
        assert "ch4" in mol_types, (
            f"{lattice_type} should place ch4, got mol_types={mol_types}"
        )
        chains[lattice_type] = SimpleNamespace(
            hydrate=hydrate, config=config
        )
    yield chains
